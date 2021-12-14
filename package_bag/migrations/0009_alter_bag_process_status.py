# Generated by Django 3.2.9 on 2021-12-06 21:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package_bag', '0008_auto_20210806_1058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bag',
            name='process_status',
            field=models.IntegerField(choices=[(1, 'Discovered'), (2, 'Assigned rights'), (3, 'Packaged'), (4, 'Delivered'), (5, 'Archived'), (11, 'Assigning rights'), (12, 'Creating package'), (13, 'Delivering'), (14, 'Creating archive')], default=1),
        ),
    ]