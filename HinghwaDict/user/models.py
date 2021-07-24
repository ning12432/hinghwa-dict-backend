from django.contrib.auth.models import User
from django.db import models


class UserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_info', verbose_name='用户',
                                primary_key=True)
    nickname = models.CharField(blank=True, max_length=100, verbose_name='昵称')
    birthday = models.DateField(blank=True, default='1970-1-1', verbose_name='生日')
    telephone = models.CharField(blank=True, max_length=50, verbose_name='电话')
    avatar = models.URLField(default='http://118.25.147.215:8080/image/defaultUser.png', blank=True, verbose_name='头像')
    county = models.CharField(blank=True, max_length=100, verbose_name="县区")
    town = models.CharField(blank=True, max_length=100, verbose_name="乡镇")