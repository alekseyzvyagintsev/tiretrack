from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import FileImport, QRCodeData, ExportBatch
from .serializers import FileImportSerializer, QRCodeDataSerializer, ExportBatchSerializer


class FileImportView(generics.CreateAPIView):
    queryset = FileImport.objects.all()
    serializer_class = FileImportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class FileImportListView(generics.ListAPIView):
    queryset = FileImport.objects.all()
    serializer_class = FileImportSerializer
    permission_classes = [IsAuthenticated]


class QRCodeDataView(generics.ListCreateAPIView):
    queryset = QRCodeData.objects.all()
    serializer_class = QRCodeDataSerializer
    permission_classes = [IsAuthenticated]


class ExportBatchView(generics.ListCreateAPIView):
    queryset = ExportBatch.objects.all()
    serializer_class = ExportBatchSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)