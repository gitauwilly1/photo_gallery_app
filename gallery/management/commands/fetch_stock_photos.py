import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from gallery.models import Photo, Tag
from cloudinary.uploader import upload

User = get_user_model()

class Command(BaseCommand):
    help = 'Fetch free stock photos from Pexels API and upload to Cloudinary'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--api-key',
            type=str,
            help='Pexels API key (get from https://www.pexels.com/api/)',
        )
        parser.add_argument(
            '--query',
            type=str,
            default='nature,landscape,photography',
            help='Search query for photos',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of photos to fetch (max 80)',
        )
    
    def handle(self, *args, **options):
        api_key = options['api_key']
        if not api_key:
            self.stdout.write(self.style.ERROR('Please provide a Pexels API key using --api-key'))
            self.stdout.write(self.style.WARNING('Get your free API key from: https://www.pexels.com/api/'))
            return
        
        query = options['query']
        count = min(options['count'], 80)
        
        # Get admin user
        admin_user = User.objects.filter(role='admin').first() or User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin user found. Please create one first.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Fetching {count} photos from Pexels for query: "{query}"...'))
        
        try:
            headers = {'Authorization': api_key}
            params = {'query': query, 'per_page': count, 'page': 1}
            
            response = requests.get(
                'https://api.pexels.com/v1/search',
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            photos = data.get('photos', [])
            
            uploaded = 0
            for photo_data in photos:
                try:
                    # Download photo
                    img_url = photo_data['src']['large']
                    img_response = requests.get(img_url)
                    
                    # Upload to Cloudinary
                    upload_result = upload(
                        img_response.content,
                        folder='photo_gallery/stock_photos',
                        public_id=f"pexels_{photo_data['id']}",
                        tags=['stock', query]
                    )
                    
                    # Create photo record
                    photo = Photo.objects.create(
                        title=photo_data.get('alt', f'Stock Photo {photo_data["id"]}')[:200],
                        description=f"Photo by {photo_data['photographer']} on Pexels",
                        user=admin_user,
                        is_approved=True,
                        is_public=True,
                    )
                    photo.image = upload_result['secure_url']
                    photo.save()
                    
                    uploaded += 1
                    self.stdout.write(f'  ✓ Uploaded: {photo.title[:50]}...')
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully uploaded {uploaded} stock photos!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching from Pexels: {str(e)}'))