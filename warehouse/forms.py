from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Document, DocumentItem, DocumentType
from tires.models import Tire, Warehouse


class DocumentForm(forms.ModelForm):
    """Форма для создания/редактирования документа"""
    
    class Meta:
        model = Document
        fields = ['document_type', 'from_warehouse', 'to_warehouse', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'from_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'to_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Фильтруем типы документов только активные
        self.fields['document_type'].queryset = DocumentType.objects.filter(is_active=True)
        
        # Фильтруем склады
        self.fields['from_warehouse'].queryset = Warehouse.objects.all()
        self.fields['to_warehouse'].queryset = Warehouse.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        document_type = cleaned_data.get('document_type')
        from_warehouse = cleaned_data.get('from_warehouse')
        to_warehouse = cleaned_data.get('to_warehouse')
        
        # Валидация для разных типов документов
        if document_type:
            if document_type.code == 'receipt':
                # Приемка - только to_warehouse
                if not to_warehouse:
                    self.add_error('to_warehouse', 'Укажите склад приемки')
            elif document_type.code == 'dispatch':
                # Отгрузка - только from_warehouse
                if not from_warehouse:
                    self.add_error('from_warehouse', 'Укажите склад отгрузки')
            elif document_type.code in ('movement', 'return'):
                # Перемещение и возврат - оба склада
                if not from_warehouse:
                    self.add_error('from_warehouse', 'Укажите склад отправления')
                if not to_warehouse:
                    self.add_error('to_warehouse', 'Укажите склад назначения')
        
        return cleaned_data


class DocumentItemForm(forms.ModelForm):
    """Форма для добавления товара в документ"""
    
    class Meta:
        model = DocumentItem
        fields = ['tire', 'quantity']
        widgets = {
            'tire': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
    
    def __init__(self, *args, **kwargs):
        document = kwargs.pop('document', None)
        super().__init__(*args, **kwargs)
        
        if document:
            # Фильтруем шины по складу отправления
            if document.from_warehouse:
                self.fields['tire'].queryset = Tire.objects.filter(
                    warehouse=document.from_warehouse,
                    is_active=True
                )
            else:
                self.fields['tire'].queryset = Tire.objects.none()
    
    def clean_tire(self):
        tire = self.cleaned_data.get('tire')
        document = self.instance.document
        
        if tire and document:
            # Проверка: шина должна быть на складе отправления
            if tire.warehouse_id != document.from_warehouse_id:
                raise ValidationError(f'Шина {tire.qr_code} находится на другом складе')
            
            # Проверка: шина не должна быть уже в других активных документах
            if tire.warehouse_document_items.filter(
                document__status__in=['saved', 'posted']
            ).exclude(document=document).exists():
                raise ValidationError(f'Шина {tire.qr_code} уже привязана к активному документу')
        
        return tire
