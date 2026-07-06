# pyrefly: ignore [missing-import]
from django.urls import path
from .views import (
    BlogListView, 
    BlogAjaxDatatableView, 
    BlogCreateView, 
    BlogUpdateView,
    BlogDetailView,
    BlogDeleteView
)

app_name = 'blog'

urlpatterns = [
    # Core Blog app routes
    path('', BlogListView.as_view(), name='list'),
    path('blogs/datatable/', BlogAjaxDatatableView.as_view(), name='datatable'),
    path('blogs/create/', BlogCreateView.as_view(), name='create'),
    path('blogs/<int:pk>/edit/', BlogUpdateView.as_view(), name='edit'),
    path('blogs/<int:pk>/', BlogDetailView.as_view(), name='detail'),
    path('blogs/<int:pk>/delete/', BlogDeleteView.as_view(), name='delete'),
]
