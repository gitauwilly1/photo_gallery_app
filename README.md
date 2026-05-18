# Photo Gallery App

A modern Django photo gallery application built with cloud storage, social authentication, and polished glassmorphism UI styling. The project supports user registration, Google social login, image uploads, likes, comments, tags, favorites, and responsive gallery browsing.

## Features

- Django 4.2 application with custom user model
- Google social login via `django-allauth`
- Cloudinary media storage for images
- PostgreSQL database support via `dj-database-url`
- Responsive Tailwind-inspired UI with glassmorphism design
- Photo gallery browse, upload, edit, delete, like, comment, and tag filtering
- Secure production settings for Render deployment

## Tech Stack

- Python 3.12
- Django 4.2
- PostgreSQL
- Cloudinary
- Django Allauth
- Gunicorn
- Whitenoise

## Project Structure

- `photogallery/` - Django project settings, URLs, WSGI
- `accounts/` - User authentication, profile, dashboard
- `gallery/` - Photo, tag, like, comment, favorite models and views
- `core/` - Landing pages and global views
- `templates/` - Base and app templates
- `static/` - CSS and frontend assets

## Local Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with the required environment variables.
5. Run migrations:

```bash
python manage.py migrate
```

6. Create a superuser if needed:

```bash
python manage.py createsuperuser
```

7. Start the development server:

```bash
python manage.py runserver
```

## Environment Variables

The app uses environment variables for configuration. Example variables:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:password@host:port/dbname
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_SECRET_KEY=your-google-secret
CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret
```

> Note: The production settings file uses `DATABASE_URL` when deploying on Render.

## Render Deployment

This project is already set up for Render deployment using `photogallery/production_settings.py`.

### Recommended Render settings

- Environment: Python
- Build Command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

- Start Command:

```bash
gunicorn photogallery.wsgi:application --bind 0.0.0.0:$PORT
```

### Required Render environment variables

Set the following in Render's dashboard for your web service:

- `SECRET_KEY` — a secure Django secret key
- `DEBUG=False`
- `ALLOWED_HOSTS=photo-gallery-app.onrender.com,localhost,127.0.0.1`
- `DATABASE_URL` — the Render PostgreSQL connection string
- `GOOGLE_CLIENT_ID`
- `GOOGLE_SECRET_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

If you are using email features, also add:

- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

### Post-deploy steps

After the first deployment, run migrations on Render:

```bash
python manage.py migrate --noinput
```

If you need to create sites or an admin user, use Render shell:

```bash
git push
# then via Render dashboard shell
python manage.py createsuperuser
```
