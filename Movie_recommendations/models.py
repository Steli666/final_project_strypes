from datetime import datetime
from django.contrib.auth.models import User
from django.db import models

class Movie(models.Model):
    movieId = models.AutoField(primary_key=True)
    title = models.TextField(max_length=200)
    genres = models.TextField(max_length=200)

    def __str__(self):
        return f"{self.movieId} - {self.title} - {self.genres}"

class Review(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.FloatField()
    timestamp = models.DateTimeField(default=datetime.now())
    class Meta:
        unique_together = ('movie', 'user')

    def __str__(self):
        return f"{self.movie.title} - {self.user.username} - {self.rating}"