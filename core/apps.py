import os
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # نتجنب التنفيذ أثناء الأوامر غير المطلوبة
        if os.environ.get("RUN_MAIN") == "true":
            return

        create_initial_superuser()
        

def create_initial_superuser():
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

    if not username or not email or not password:
        return

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if User.objects.filter(is_superuser=True).exists():
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            user_type="executive",
        )
        print(f"✅ تم إنشاء المشرف الأول تلقائيًا: {username}")

    except Exception as exc:
        print(f"⚠️ تعذر إنشاء المشرف الأول تلقائيًا: {exc}")
