import logging
import pickle
from django.contrib.auth import logout
from django.http import HttpResponse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User

from .models import Movie, Review
from .serializers import UserSerializer, MovieSerializer, ReviewSerializer, GetReviewSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
import joblib
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity



logger = logging.getLogger(__name__)

class UserRegister(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(username=request.data['username'])
            token = Token.objects.create(user=user)
            return Response({"token": token.key, "user": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogin(APIView):
    def post(self, request):
        user = get_object_or_404(User, username=request.data.get('username'))
        if not user.check_password(request.data.get('password')):
            return Response({"details": "Incorrect username or password"}, status=status.HTTP_404_NOT_FOUND)
        token, created = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(instance=user)
        print(token)
        return Response({"token": token.key, "user": serializer.data}, status=status.HTTP_200_OK)

class UserLogout(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.auth_token.delete()
        logout(request)
        return Response({"details": "You have logged out"}, status=status.HTTP_200_OK)

class RecommendationSimilarity(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        cv = joblib.load('Movie_recommendations/RecommendationSimilarity/count_vectorizer.pkl')
        similarity = joblib.load('Movie_recommendations/RecommendationSimilarity/similarity_matrix.pkl')
        new_df = pd.read_pickle('Movie_recommendations/RecommendationSimilarity/movies_df.pkl')

        original_titles = new_df['title']
        new_df['title'] = new_df['title'].str.lower()
        title_mapping = pd.Series(original_titles.values, index=new_df['title']).to_dict()

        movie = request.query_params.get('movie', None)
        if movie is None:
            return Response({"error": "No movie title provided"}, status=400)

        movie = movie.lower()

        def recommend(movie):
            movie_index = new_df[new_df['title'] == movie].index[0]
            distances = similarity[movie_index]
            movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
            recommended_movies = [new_df.iloc[i[0]].title for i in movies_list]
            return recommended_movies

        try:
            recommendations = recommend(movie)
            recommendations = [title_mapping[title] for title in recommendations]
            return Response({"recommendations": recommendations}, status=200)
        except IndexError:
            return Response({"error": "Movie not found"}, status=404)


class RecommendationRating(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        with open('Movie_recommendations/RecommendationRating/movie_rating_user.pkl', 'rb') as f:
            movie_rating_user = pickle.load(f)

        with open('Movie_recommendations/RecommendationRating/rating_mean_count.pkl', 'rb') as f:
            rating_mean_count = pickle.load(f)

        movie = request.query_params.get('movie', None)

        if movie is None:
            return Response({"error": "No movie title provided"}, status=400)

        movie = movie.lower()
        movie_titles = {col.lower(): col for col in movie_rating_user.columns}

        def clean_title(title):
            return title.lower().split('(')[0].strip()

        cleaned_movie_titles = {clean_title(title): title for title in movie_titles.values()}

        def get_similar_movies(movie_title, min_ratings=100):
            if movie_title not in cleaned_movie_titles:
                return None

            original_title = cleaned_movie_titles[movie_title]
            movie_ratings = movie_rating_user[original_title]
            similar_movies = movie_rating_user.corrwith(movie_ratings)

            movie_corr = pd.DataFrame(similar_movies, columns=['Correlation'])
            movie_corr.dropna(inplace=True)

            movie_corr = movie_corr.join(rating_mean_count['rating_counts'])

            result = movie_corr[movie_corr['rating_counts'] > min_ratings].sort_values('Correlation', ascending=False)

            return result

        try:
            cleaned_movie = clean_title(movie)
            similar_movies = get_similar_movies(cleaned_movie)
            if similar_movies is None:
                return Response({"error": "Movie not found"}, status=404)

            recommendations = similar_movies.head().reset_index()[['title', 'Correlation']].to_dict(orient='records')

            return Response({"recommendations": recommendations}, status=200)
        except IndexError:
            return Response({"error": "An error occurred while processing the request"}, status=500)


class AddReviews(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        movie_data = request.data.get('movie')
        rating_data = request.data.get('rating')

        if not movie_data:
            return Response({"error": "Movie data is required"}, status=status.HTTP_400_BAD_REQUEST)

        movie_serializer = MovieSerializer(data=movie_data)
        if movie_serializer.is_valid():
            movie, created = Movie.objects.get_or_create(
                title=movie_serializer.validated_data['title'],
                genres=movie_serializer.validated_data['genres'],
                defaults={'movieId': movie_serializer.validated_data.get('movieId')}
            )

            rating_data['movie'] = movie.movieId
            review_serializer = ReviewSerializer(data=rating_data)
            if review_serializer.is_valid():
                Review.objects.create(
                    movie=movie,
                    user=request.user,
                    rating=review_serializer.validated_data['rating']
                )
                return Response({"message": "Review created successfully"}, status=status.HTTP_201_CREATED)
            else:
                return Response(review_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(movie_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserReviews(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        reviews = Review.objects.filter(user=user)
        serializer = GetReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)