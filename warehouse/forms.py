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
        document = kwargs.pop('document', None)
        super().__init__(*args, **kwargs)
        
        # Фильтруем типы документов только активные
        self.fields['document_type'].queryset = DocumentType.objects.filter(is_active=True)
        
        # Фильтруем склады
        self.fields['from_warehouse'].queryset = Warehouse.objects.all()
        self.fields['to_warehouse'].queryset = Warehouse.objects.all()
        
        # Если документ уже сохранен (есть id и document_number), поле document_type неактивно
        if document and document.id and document.document_number:
            self.fields['document_type'].widget.attrs['readonly'] = True
    
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
        fields = ['product_name', 'quantity']
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
    
    def __init__(self, *args, **kwargs):
        document = kwargs.pop('document', None)
        super().__init__(*args, **kwargs)
        
        self.document = document
        
        if document and document.from_warehouse:
            # Получаем product_name из шин на складе
            product_names = Tire.objects.filter(
                warehouse=document.from_warehouse,
                is_active=True
            ).values_list('product_name', flat=True).distinct()
            
            self.fields['product_name'].widget = forms.Select(choices=[(pn, pn) for pn in product_names])
        else:
            self.fields['product_name'].widget = forms.TextInput()
    
    def clean(self):
        cleaned_data = super().clean()
        product_name = cleaned_data.get('product_name')
        quantity = cleaned_data.get('quantity')
        
        if product_name and self.document:
            # Проверка доступного количества
            available_count = Tire.objects.filter(
                product_name=product_name,
                warehouse=self.document.from_warehouse,
                is_active=True
            ).count()
            
            if quantity > available_count:
                raise ValidationError(f'Недостаточно шин. Доступно {available_count} шт.')
        
        return cleaned_data
