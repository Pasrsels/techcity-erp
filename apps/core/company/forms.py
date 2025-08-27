from django import forms
from .models import Branch, Company

class BranchForm(forms.ModelForm):
    from_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=False,
        label="Merge From Branch",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    # options = forms.MultipleChoiceField(
    #     choices=[
    #         ('products', 'Products'),
    #         ('suppliers', 'Suppliers'),
    #     ],
    #     widget=forms.CheckboxSelectMultiple(),
    #     required=False,
    #     label="Merge Options",
    # )

    class Meta:
        model = Branch
        fields = '__all__'



class CompanyRegistrationForm(forms.ModelForm):

    class Meta:
        model = Company
        fields = '__all__'
