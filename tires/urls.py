from django.urls import path
from . import views

app_name = 'tires'

urlpatterns = [
    path('owners/', views.OwnerListCreateView.as_view(), name='owner-list'),
    path('owners/<int:pk>/', views.OwnerDetailView.as_view(), name='owner-detail'),
    
    path('tires/', views.TireListCreateView.as_view(), name='tire-list'),
    path('tires/<int:pk>/', views.TireDetailView.as_view(), name='tire-detail'),
    
    path('transfers/', views.TireTransferView.as_view(), name='tire-transfer'),
    path('transfers/history/', views.TireTransferListView.as_view(), name='transfer-history'),
]