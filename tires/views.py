from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Tire, Owner, TireTransfer
from .serializers import TireSerializer, OwnerSerializer, TireTransferSerializer


class OwnerListCreateView(generics.ListCreateAPIView):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    permission_classes = [IsAuthenticated]


class OwnerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    permission_classes = [IsAuthenticated]


class TireListCreateView(generics.ListCreateAPIView):
    queryset = Tire.objects.all()
    serializer_class = TireSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Tire.objects.all()
        status = self.request.query_params.get('status', None)
        owner = self.request.query_params.get('owner', None)
        
        if status is not None:
            queryset = queryset.filter(status=status)
        if owner is not None:
            queryset = queryset.filter(owner=owner)
            
        return queryset


class TireDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tire.objects.all()
    serializer_class = TireSerializer
    permission_classes = [IsAuthenticated]


class TireTransferView(generics.CreateAPIView):
    queryset = TireTransfer.objects.all()
    serializer_class = TireTransferSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(transferred_by=self.request.user)


class TireTransferListView(generics.ListAPIView):
    queryset = TireTransfer.objects.all()
    serializer_class = TireTransferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TireTransfer.objects.all()
        tire_qr_code = self.request.query_params.get('tire_qr_code', None)
        
        if tire_qr_code is not None:
            queryset = queryset.filter(tire__qr_code=tire_qr_code)
            
        return queryset