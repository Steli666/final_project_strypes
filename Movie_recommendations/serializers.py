from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Movie, Review


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ['movieId', 'title', 'genres']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['movie', 'rating']

class GetReviewSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source='movie.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['movie_title', 'rating', 'timestamp', 'user_username']



# class ReviewSerializer(serializers.ModelSerializer):
#     movie_title = serializers.CharField(source='movie.title')
#
#     class Meta:
#         model = Review
#         fields = ['movie_title', 'rating', 'timestamp']