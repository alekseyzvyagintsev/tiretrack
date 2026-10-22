from django.urls import path

from . import views

app_name = 'warehouse'

urlpatterns = [
    # Домашняя страница
    path('', views.homepage, name='home'),

    # Документы
    path('documents/', views.document_list, name='document-list'),
    path('documents/new/', views.document_create, name='document-create'),
    path('documents/<int:pk>/', views.document_detail, name='document-detail'),
    path('documents/<int:pk>/save/', views.document_save, name='document-save'),
    path('documents/<int:pk>/post/', views.document_post, name='document-post'),
    path('documents/<int:pk>/unpost/', views.document_unpost, name='document-unpost'),
    path('documents/<int:pk>/delete/', views.document_mark_deleted, name='document-delete'),

    # AJAX
    path('documents/<int:pk>/add-item/', views.document_add_item, name='document-add-item'),
    path('documents/<int:pk>/items/<int:item_pk>/update/', views.document_update_item, name='document-update-item'),
    path('documents/<int:pk>/items/<int:item_pk>/delete/', views.document_delete_item, name='document-delete-item'),
    path('documents/<int:pk>/autosave/', views.document_autosave, name='document-autosave'),
    path('api/nomenclature/search/', views.nomenclature_search, name='nomenclature-search'),
    path('documents/<int:pk>/codes/', views.document_codes, name='document-codes'),
    path('api/counters/', views.counters_api, name='counters-api'),
    path('codes/<int:code_id>/card/', views.code_card, name='code-card'),
]
