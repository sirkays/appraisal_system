from django import forms
from accounts.models import CustomUser
from departments.models import Department

class StaffForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to use the default password 'sirs2026' for new users."
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone', 
            'role', 'department', 'designation', 'supervisor', 'password'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            classes = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm'
            if isinstance(field.widget, forms.Select):
                classes += ' select2-search'
            field.widget.attrs.update({'class': classes})

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if not self.instance.pk:
            # New user
            if password:
                user.set_password(password)
            else:
                user.set_password("sirs2026")
        else:
            # Existing user - only update password if provided
            if password:
                user.set_password(password)

        if commit:
            user.save()
        return user

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'hod']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            classes = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm'
            if isinstance(field.widget, forms.Select):
                classes += ' select2-search'
            field.widget.attrs.update({'class': classes})
