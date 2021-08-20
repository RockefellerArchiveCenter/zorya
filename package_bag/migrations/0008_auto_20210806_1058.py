# Generated by Django 3.2.5 on 2021-08-06 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package_bag', '0007_auto_20210614_1157'),
    ]

    operations = [
        migrations.AddField(
            model_name='bag',
            name='data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bag',
            name='process_status',
            field=models.IntegerField(choices=[(1, 'Discovered'), (2, 'Assigned rights'), (3, 'Packaged'), (4, 'Delivered')], default=1),
        ),
        migrations.AddField(
            model_name='bag',
            name='type',
            field=models.CharField(blank=True, choices=[('aip', 'Archival Information Package'), ('dip', 'Dissemination Information Package')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='bag',
            name='bag_path',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]