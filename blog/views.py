from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from .decorators import content_manager_required
from .models import BlogPost


# Только контент-менеджеры могут создавать/редактировать блог
@method_decorator(content_manager_required, name="dispatch")
class BlogPostCreateView(LoginRequiredMixin, CreateView):
    model = BlogPost
    fields = ["title", "content", "is_published"]
    template_name = "blog/blogpost_form.html"
    success_url = reverse_lazy("blog:list")

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


@method_decorator(content_manager_required, name="dispatch")
class BlogPostUpdateView(LoginRequiredMixin, UpdateView):
    model = BlogPost
    fields = ["title", "content", "is_published"]
    template_name = "blog/blogpost_form.html"
    success_url = reverse_lazy("blog:list")


# Все могут просматривать опубликованные записи
class BlogPostListView(ListView):
    model = BlogPost
    template_name = "blog/blogpost_list.html"
    context_object_name = "posts"

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)
