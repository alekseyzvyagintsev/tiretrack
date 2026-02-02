from rest_framework import serializers
from .models import FileImport, QRCodeData, ExportBatch


class FileImportSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = FileImport
        fields = '__all__'
        read_only_fields = ('uploaded_by', 'upload_date', 'processed', 'success_count', 'error_count')


class QRCodeDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRCodeData
        fields = '__all__'


class ExportBatchSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ExportBatch
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'completed')