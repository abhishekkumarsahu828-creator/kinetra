from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image
from .models import Resource, Booking, ConditionReport, Incident, Organisation, Membership, Credential, Blackout

class StyledFormMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            widget=field.widget
            base=widget.attrs.get('class','')
            widget.attrs['class']=(base+' form-control').strip()
            if isinstance(widget,(forms.Textarea,)):
                widget.attrs.setdefault('rows',3)

class SignupForm(StyledFormMixin,UserCreationForm):
    first_name=forms.CharField(max_length=50)
    last_name=forms.CharField(max_length=50)
    email=forms.EmailField()
    organisation=forms.ModelChoiceField(queryset=Organisation.objects.filter(is_active=True),empty_label='Select an institution')
    class Meta:
        model=User
        fields=('first_name','last_name','username','email','organisation','password1','password2')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['organisation'].label_from_instance=lambda org: f'{org.name} · DEMO' if org.slug.startswith('kinetra-demo-') else org.name
        self.fields['organisation'].help_text='Organisations marked DEMO are fictional preview data.'
    def clean_email(self):
        email=self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists(): raise ValidationError('This email is already registered.')
        return email

def validate_photo(upload):
    if not upload: return upload
    if upload.size > 5*1024*1024: raise ValidationError('Maximum image size is 5 MB.')
    try:
        img=Image.open(upload)
        img.verify()
        if img.format not in ('PNG','JPEG','WEBP'): raise ValueError()
    except Exception:
        raise ValidationError('Use a valid JPEG, PNG or WebP image.')
    finally:
        upload.seek(0)
    return upload

class ResourceForm(StyledFormMixin,forms.ModelForm):
    class Meta:
        model=Resource
        fields=['name','category','summary','description','location','equipment_specs','usage_rules',
                'required_training','requires_supervision','max_hours','weekly_hours_limit','advance_booking_days',
                'open_time','close_time','available_days','image','status']
        widgets={'open_time':forms.TimeInput(attrs={'type':'time'}),'close_time':forms.TimeInput(attrs={'type':'time'}),
                 'available_days':forms.TextInput(attrs={'placeholder':'0,1,2,3,4,5  (Monday=0)'}),
                 'description':forms.Textarea(attrs={'rows':4})}
        help_texts={'available_days':'Comma-separated weekdays; Monday=0, Sunday=6.',
                    'required_training':'Leave blank if verified training is not required.'}
    def clean_image(self): return validate_photo(self.cleaned_data.get('image'))
    def clean_available_days(self):
        raw=self.cleaned_data['available_days']
        parts=[p.strip() for p in raw.split(',')]
        if not parts or any(p not in '0123456' or len(p)!=1 for p in parts):
            raise ValidationError('Use weekday numbers 0–6 separated by commas.')
        return ','.join(sorted(set(parts)))

class BookingForm(StyledFormMixin,forms.ModelForm):
    start=forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(date_attrs={'type':'date'},time_attrs={'type':'time'}))
    end=forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(date_attrs={'type':'date'},time_attrs={'type':'time'}))
    class Meta:
        model=Booking
        fields=['start','end','purpose']
        widgets={'purpose':forms.Textarea(attrs={'placeholder':'Briefly describe your project or intended use.'})}

class ConditionForm(StyledFormMixin,forms.ModelForm):
    class Meta:
        model=ConditionReport
        fields=['condition','notes','evidence']
    def clean_evidence(self): return validate_photo(self.cleaned_data.get('evidence'))

class IncidentForm(StyledFormMixin,forms.ModelForm):
    class Meta:
        model=Incident
        fields=['category','description']

class CredentialForm(StyledFormMixin,forms.ModelForm):
    class Meta:
        model=Credential
        fields=['title']

class BlackoutForm(StyledFormMixin,forms.ModelForm):
    start=forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(date_attrs={'type':'date'},time_attrs={'type':'time'}))
    end=forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(date_attrs={'type':'date'},time_attrs={'type':'time'}))
    class Meta:
        model=Blackout
        fields=['start','end','reason']
    def clean(self):
        data=super().clean()
        if data.get('start') and data.get('end') and data['start']>=data['end']:
            raise ValidationError('End must be after start.')
        return data
