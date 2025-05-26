from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Industry(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, blank=True)  # Emoji or icon class
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Industries"

class Startup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='startups')
    location = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    logo = models.CharField(max_length=10, default='🚀')  # Emoji logo
    
    # Financial info
    funding_amount = models.CharField(max_length=20, blank=True)
    valuation = models.CharField(max_length=20, blank=True)
    
    # Company details
    employee_count = models.PositiveIntegerField(default=0)
    founded_year = models.PositiveIntegerField()
    is_featured = models.BooleanField(default=False)
    
    # Metrics
    revenue = models.CharField(max_length=20, blank=True)
    user_count = models.CharField(max_length=20, blank=True)
    growth_rate = models.CharField(max_length=10, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return self.name
    
    @property
    def average_rating(self):
        ratings = self.ratings.all()
        if ratings:
            return sum(r.rating for r in ratings) / len(ratings)
        return 0
    
    @property
    def total_ratings(self):
        return self.ratings.count()

class StartupFounder(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='founders')
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, default='Co-Founder')
    bio = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.startup.name}"

class StartupTag(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='tags')
    tag = models.CharField(max_length=30)
    
    class Meta:
        unique_together = ['startup', 'tag']
        
    def __str__(self):
        return self.tag

class StartupRating(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['startup', 'user']

class StartupComment(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    likes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class StartupBookmark(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['startup', 'user']

class StartupLike(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['startup', 'user']
