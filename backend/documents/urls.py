from django.urls import path
from .views import DocumentUploadView, DocumentDetailView, DocumentIndexView, SearchView, AskView

urlpatterns = [
    path("documents/", DocumentUploadView.as_view(), name="document-upload"),
    path("documents/<int:doc_id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<int:doc_id>/index/", DocumentIndexView.as_view(), name="document-index"),
    path("search/", SearchView.as_view(), name="search"),
    path("ask/", AskView.as_view(), name="ask"),

]
