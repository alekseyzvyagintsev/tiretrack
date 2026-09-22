from django import forms
from django.core.exceptions import ValidationError

from .models import Document, DocumentItem, DocType
from tires.models import TireNomenclature, Warehouse


class DocumentForm(forms.ModelForm):
    """Форма для создания/редактирования документа."""

    class Meta:
        model = Document
        fields = ['doc_type', 'source_warehouse', 'target_warehouse', 'notes']
        widgets = {
            'doc_type': forms.Select(attrs={'class': 'form-select'}),
            'source_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'target_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        document = kwargs.pop('document', None)
        super().__init__(*args, **kwargs)

        # Фильтруем типы документов только активные
        self.fields['doc_type'].queryset = DocType.objects.filter(is_active=True)

        # Фильтруем склады по площадке пользователя
        if user and hasattr(user, 'platform') and user.platform:
            self.fields['source_warehouse'].queryset = Warehouse.objects.filter(
                platform=user.platform
            )
            self.fields['target_warehouse'].queryset = Warehouse.objects.filter(
                platform=user.platform
            )
        else:
            self.fields['source_warehouse'].queryset = Warehouse.objects.all()
            self.fields['target_warehouse'].queryset = Warehouse.objects.all()


class DocumentItemForm(forms.ModelForm):
    """Форма для добавления позиции в документ."""

    class Meta:
        model = DocumentItem
        fields = ['nomenclature', 'quantity']
        widgets = {
            'nomenclature': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nomenclature'].queryset = TireNomenclature.objects.filter(is_active=True)
