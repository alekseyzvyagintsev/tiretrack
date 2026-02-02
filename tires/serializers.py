from rest_framework import serializers
from .models import Tire, Owner, TireTransfer


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = '__all__'


class TireSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    
    class Meta:
        model = Tire
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TireTransferSerializer(serializers.ModelSerializer):
    tire_qr_code = serializers.CharField(source='tire.qr_code', read_only=True)
    from_owner_name = serializers.CharField(source='from_owner.name', read_only=True)
    to_owner_name = serializers.CharField(source='to_owner.name', read_only=True)
    transferred_by_name = serializers.CharField(source='transferred_by.get_full_name', read_only=True)
    
    class Meta:
        model = TireTransfer
        fields = '__all__'
        read_only_fields = ('transferred_by', 'transfer_date')