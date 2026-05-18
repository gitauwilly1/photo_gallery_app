"""
Management command to upload sample images to Cloudinary
"""

import os
import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from gallery.models import Photo, Tag
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from django.core.files.base import ContentFile
from io import BytesIO

User = get_user_model()

# Working sample images from reliable sources
SAMPLE_IMAGES = [
    {
        'url': 'https://images.pexels.com/photos/417074/pexels-photo-417074.jpeg?w=800',
        'title': 'Mountain Sunset',
        'description': 'Breathtaking sunset over the majestic mountains with golden hues painting the sky.',
        'tags': ['nature', 'sunset', 'mountains', 'landscape'],
        'camera': {'make': 'Nikon', 'model': 'D850', 'aperture': 'f/8', 'shutter': '1/250', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/457882/pexels-photo-457882.jpeg?w=800',
        'title': 'Ocean Waves',
        'description': 'Powerful ocean waves crashing against the rocky shoreline at golden hour.',
        'tags': ['ocean', 'waves', 'beach', 'seascape'],
        'camera': {'make': 'Canon', 'model': '5D Mark IV', 'aperture': 'f/11', 'shutter': '1/500', 'iso': '200'}
    },
    {
        'url': 'https://images.pexels.com/photos/158607/forest-trees-path-158607.jpeg?w=800',
        'title': 'Forest Path',
        'description': 'Mysterious forest path surrounded by ancient trees and filtered sunlight.',
        'tags': ['forest', 'nature', 'trees', 'path'],
        'camera': {'make': 'Sony', 'model': 'A7R III', 'aperture': 'f/4', 'shutter': '1/125', 'iso': '400'}
    },
    {
        'url': 'https://images.pexels.com/photos/373912/pexels-photo-373912.jpeg?w=800',
        'title': 'City Lights',
        'description': 'Vibrant city skyline illuminated by countless lights at night.',
        'tags': ['city', 'urban', 'night', 'architecture'],
        'camera': {'make': 'Fujifilm', 'model': 'X-T4', 'aperture': 'f/2.8', 'shutter': '1/60', 'iso': '800'}
    },
    {
        'url': 'https://images.pexels.com/photos/2387873/pexels-photo-2387873.jpeg?w=800',
        'title': 'Desert Dunes',
        'description': 'Golden sand dunes stretching endlessly under the blazing sun.',
        'tags': ['desert', 'sand', 'landscape', 'dunes'],
        'camera': {'make': 'Nikon', 'model': 'Z7', 'aperture': 'f/9', 'shutter': '1/400', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/147411/italy-mountains-dawn-daybreak-147411.jpeg?w=800',
        'title': 'Mountain Lake',
        'description': 'Crystal clear mountain lake reflecting the surrounding peaks.',
        'tags': ['mountain', 'lake', 'nature', 'water'],
        'camera': {'make': 'Canon', 'model': 'EOS R', 'aperture': 'f/7.1', 'shutter': '1/30', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/731082/pexels-photo-731082.jpeg?w=800',
        'title': 'Autumn Forest',
        'description': 'Vibrant autumn leaves creating a colorful forest canopy.',
        'tags': ['autumn', 'fall', 'colors', 'trees'],
        'camera': {'make': 'Sony', 'model': 'A7 IV', 'aperture': 'f/5.6', 'shutter': '1/200', 'iso': '200'}
    },
    {
        'url': 'https://images.pexels.com/photos/355465/pexels-photo-355465.jpeg?w=800',
        'title': 'Snowy Peak',
        'description': 'Pristine snow-covered mountain peak under clear blue sky.',
        'tags': ['snow', 'mountains', 'winter', 'landscape'],
        'camera': {'make': 'Fujifilm', 'model': 'GFX 100', 'aperture': 'f/11', 'shutter': '1/500', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/247502/pexels-photo-247502.jpeg?w=800',
        'title': 'Wildlife Portrait',
        'description': 'Stunning close-up portrait of a wild animal in its natural habitat.',
        'tags': ['wildlife', 'animals', 'nature', 'portrait'],
        'camera': {'make': 'Nikon', 'model': 'D500', 'aperture': 'f/5.6', 'shutter': '1/1000', 'iso': '400'}
    },
    {
        'url': 'https://images.pexels.com/photos/206172/pexels-photo-206172.jpeg?w=800',
        'title': 'Modern Architecture',
        'description': 'Modern architectural design showcasing geometric patterns and symmetry.',
        'tags': ['architecture', 'design', 'urban', 'modern'],
        'camera': {'make': 'Canon', 'model': '6D Mark II', 'aperture': 'f/8', 'shutter': '1/125', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/585419/pexels-photo-585419.jpeg?w=800',
        'title': 'Street Photography',
        'description': 'Candid street photography capturing everyday life moments.',
        'tags': ['street', 'urban', 'people', 'life'],
        'camera': {'make': 'Leica', 'model': 'Q2', 'aperture': 'f/2', 'shutter': '1/500', 'iso': '200'}
    },
    {
        'url': 'https://images.pexels.com/photos/56866/garden-rose-red-pink-56866.jpeg?w=800',
        'title': 'Floral Beauty',
        'description': 'Delicate flower petals with soft natural lighting.',
        'tags': ['flowers', 'nature', 'macro', 'beauty'],
        'camera': {'make': 'Sony', 'model': 'A7R IV', 'aperture': 'f/2.8', 'shutter': '1/250', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/814499/pexels-photo-814499.jpeg?w=800',
        'title': 'Waterfall Wonder',
        'description': 'Cascading waterfall surrounded by lush green vegetation.',
        'tags': ['waterfall', 'nature', 'water', 'forest'],
        'camera': {'make': 'Nikon', 'model': 'Z6', 'aperture': 'f/8', 'shutter': '1/30', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/210186/pexels-photo-210186.jpeg?w=800',
        'title': 'Golden Hour Beach',
        'description': 'Beautiful beach during golden hour with soft warm light.',
        'tags': ['beach', 'sunset', 'ocean', 'golden hour'],
        'camera': {'make': 'Canon', 'model': '5D Mark III', 'aperture': 'f/5.6', 'shutter': '1/200', 'iso': '200'}
    },
    {
        'url': 'https://images.pexels.com/photos/36717/amazing-animal-beautiful-beautifull.jpg?w=800',
        'title': 'Butterfly Macro',
        'description': 'Detailed macro shot of a butterfly showing intricate wing patterns.',
        'tags': ['butterfly', 'macro', 'insect', 'nature'],
        'camera': {'make': 'Sony', 'model': 'A7R III', 'aperture': 'f/3.5', 'shutter': '1/500', 'iso': '100'}
    },
    {
        'url': 'https://images.pexels.com/photos/169647/pexels-photo-169647.jpeg?w=800',
        'title': 'Night Sky Stars',
        'description': 'Amazing night sky filled with countless stars and Milky Way.',
        'tags': ['night', 'stars', 'astronomy', 'sky'],
        'camera': {'make': 'Nikon', 'model': 'D810', 'aperture': 'f/2.8', 'shutter': '30s', 'iso': '1600'}
    },
    {
        'url': 'https://images.pexels.com/photos/460672/pexels-photo-460672.jpeg?w=800',
        'title': 'Cherry Blossoms',
        'description': 'Beautiful cherry blossom trees in full bloom during spring.',
        'tags': ['cherry blossom', 'spring', 'flowers', 'pink'],
        'camera': {'make': 'Fujifilm', 'model': 'X-T3', 'aperture': 'f/4', 'shutter': '1/400', 'iso': '200'}
    },
    {
        'url': 'https://images.pexels.com/photos/531880/pexels-photo-531880.jpeg?w=800',
        'title': 'Fireworks Display',
        'description': 'Spectacular fireworks display lighting up the night sky.',
        'tags': ['fireworks', 'celebration', 'night', 'city'],
        'camera': {'make': 'Sony', 'model': 'A7S II', 'aperture': 'f/8', 'shutter': '2s', 'iso': '400'}
    }
]

class Command(BaseCommand):
    help = 'Upload sample images to Cloudinary and create photo records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete existing photos before uploading new ones',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting sample images upload to Cloudinary...'))
        
        # Get or create admin user
        admin_user = User.objects.filter(role='admin').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin or superuser found. Please create one first.'))
            self.stdout.write(self.style.WARNING('Run: python manage.py createsuperuser'))
            return
        
        # Delete existing photos if flag is set
        if options['delete_existing']:
            photo_count = Photo.objects.count()
            Photo.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {photo_count} existing photos'))
        
        # Create tags if they don't exist
        all_tags = set()
        for img in SAMPLE_IMAGES:
            for tag_name in img['tags']:
                all_tags.add(tag_name)
        
        tag_objects = {}
        for tag_name in all_tags:
            tag, created = Tag.objects.get_or_create(name=tag_name.lower())
            tag_objects[tag_name] = tag
            if created:
                self.stdout.write(f'Created tag: {tag_name}')
        
        # Upload images to Cloudinary
        uploaded_count = 0
        failed_count = 0
        
        for idx, img_data in enumerate(SAMPLE_IMAGES):
            self.stdout.write(f'Uploading {idx + 1}/{len(SAMPLE_IMAGES)}: {img_data["title"]}...')
            
            try:
                # Download image from URL
                response = requests.get(img_data['url'], timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                # Upload to Cloudinary
                upload_result = upload(
                    response.content,
                    folder='photo_gallery/sample_photos',
                    public_id=img_data['title'].lower().replace(' ', '_').replace('-', '_'),
                    overwrite=True,
                    tags=','.join(img_data['tags'])
                )
                
                # Create photo record in database
                photo = Photo.objects.create(
                    title=img_data['title'],
                    description=img_data['description'],
                    user=admin_user,
                    is_approved=True,
                    is_public=True,
                    is_featured=(idx < 6),  # First 6 images are featured
                    camera_make=img_data['camera'].get('make', ''),
                    camera_model=img_data['camera'].get('model', ''),
                    aperture=img_data['camera'].get('aperture', ''),
                    shutter_speed=img_data['camera'].get('shutter', ''),
                    iso=img_data['camera'].get('iso', ''),
                )
                
                # Store the Cloudinary URL correctly
                if hasattr(upload_result, 'url'):
                    photo.image = upload_result.url
                elif isinstance(upload_result, dict):
                    photo.image = upload_result.get('secure_url', upload_result.get('url', ''))
                else:
                    photo.image = str(upload_result)
                
                photo.save()
                
                # Add tags
                for tag_name in img_data['tags']:
                    if tag_name in tag_objects:
                        photo.tags.add(tag_objects[tag_name])
                
                uploaded_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Uploaded: {img_data["title"]}'))
                
            except requests.exceptions.RequestException as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Network error for {img_data["title"]}: {str(e)}'))
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to upload {img_data["title"]}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully uploaded {uploaded_count} images to Cloudinary!'))
        self.stdout.write(self.style.WARNING(f'Failed to upload {failed_count} images'))
        self.stdout.write(self.style.SUCCESS(f'Total photos in database: {Photo.objects.count()}'))
        
        # Print sample URLs for verification
        if uploaded_count > 0:
            self.stdout.write(self.style.WARNING('\nSample Cloudinary URLs:'))
            sample_photos = Photo.objects.filter(is_featured=True)[:3]
            for photo in sample_photos:
                # Safely get the image URL
                image_url = str(photo.image) if photo.image else 'No URL'
                url_preview = image_url[:80] if len(image_url) > 80 else image_url
                self.stdout.write(f'  - {photo.title}: {url_preview}...')