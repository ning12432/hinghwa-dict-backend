# Generated by Django 3.0.6 on 2021-08-11 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('word', '0007_auto_20210811_1737'),
    ]

    operations = [
        migrations.AlterField(
            model_name='word',
            name='annotation',
            field=models.TextField(blank=True, verbose_name='附注'),
        ),
        migrations.AlterField(
            model_name='word',
            name='mandarin',
            field=models.TextField(blank=True, verbose_name='对应普通话词语'),
        ),
    ]