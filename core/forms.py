from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User, Institution


class ArabicLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="اسم المستخدم",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "اسم المستخدم",
            }
        ),
    )
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "كلمة المرور",
            }
        ),
    )


class RegisterForm(UserCreationForm):
    username = forms.CharField(
        label="اسم المستخدم",
        help_text="",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label="الاسم الأول",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="الاسم الأخير",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label="رقم الجوال",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    national_id = forms.CharField(
        label="رقم الهوية / السجل",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    business_name = forms.CharField(
        label="اسم المنشأة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    business_unified_number = forms.CharField(
        label="الرقم الموحد للمنشأة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    user_type = forms.ChoiceField(
        label="نوع المستخدم",
        choices=User.USER_TYPES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password1 = forms.CharField(
        label="كلمة المرور",
        help_text="",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        help_text="",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "national_id",
            "business_name",
            "business_unified_number",
            "user_type",
            "password1",
            "password2",
        ]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("اسم المستخدم مستخدم مسبقاً")
        return username

    def clean_national_id(self):
        national_id = (self.cleaned_data.get("national_id") or "").strip()
        if national_id and User.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError("رقم الهوية / السجل مستخدم مسبقاً")
        return national_id

    def clean_business_unified_number(self):
        business_unified_number = (self.cleaned_data.get("business_unified_number") or "").strip()
        if business_unified_number and User.objects.filter(business_unified_number=business_unified_number).exists():
            raise forms.ValidationError("الرقم الموحد للمنشأة مستخدم مسبقاً")
        return business_unified_number


class CreateUserForm(UserCreationForm):
    username = forms.CharField(
        label="اسم المستخدم",
        help_text="",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label="الاسم الأول",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="الاسم الأخير",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label="رقم الجوال",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    national_id = forms.CharField(
        label="رقم الهوية / السجل",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    business_name = forms.CharField(
        label="اسم المنشأة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    business_unified_number = forms.CharField(
        label="الرقم الموحد للمنشأة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    user_type = forms.ChoiceField(
        label="نوع المستخدم",
        choices=User.USER_TYPES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password1 = forms.CharField(
        label="كلمة المرور",
        help_text="",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        help_text="",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "national_id",
            "business_name",
            "business_unified_number",
            "user_type",
            "password1",
            "password2",
        ]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("اسم المستخدم مستخدم مسبقاً")
        return username

    def clean_national_id(self):
        national_id = (self.cleaned_data.get("national_id") or "").strip()
        if national_id and User.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError("رقم الهوية / السجل مستخدم مسبقاً")
        return national_id

    def clean_business_unified_number(self):
        business_unified_number = (self.cleaned_data.get("business_unified_number") or "").strip()
        if business_unified_number and User.objects.filter(business_unified_number=business_unified_number).exists():
            raise forms.ValidationError("الرقم الموحد للمنشأة مستخدم مسبقاً")
        return business_unified_number


class ClientProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label="الاسم الأول",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="الاسم الأخير",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label="رقم الجوال",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    national_id = forms.CharField(
        label="رقم الهوية / الإقامة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    business_name = forms.CharField(
        label="اسم المنشأة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    business_unified_number = forms.CharField(
        label="الرقم الموحد للمنشأة",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "national_id",
            "business_name",
            "business_unified_number",
        ]

    def clean_national_id(self):
        national_id = (self.cleaned_data.get("national_id") or "").strip()
        if national_id:
            qs = User.objects.filter(national_id=national_id)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("رقم الهوية / الإقامة مستخدم من قبل.")
        return national_id

    def clean_business_unified_number(self):
        business_unified_number = (self.cleaned_data.get("business_unified_number") or "").strip()
        if business_unified_number:
            qs = User.objects.filter(business_unified_number=business_unified_number)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("الرقم الموحد للمنشأة مستخدم من قبل.")
        return business_unified_number


class InstitutionForm(forms.ModelForm):
    name = forms.CharField(
        label="اسم المؤسسة",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    unified_number = forms.CharField(
        label="الرقم الموحد",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    executive_name = forms.CharField(
        label="اسم المدير التنفيذي",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Institution
        fields = [
            "name",
            "unified_number",
            "executive_name",
            "logo",
            "letterhead",
            "stamp",
            "signature",
        ]
