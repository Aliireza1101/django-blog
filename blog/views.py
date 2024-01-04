from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Model, Manager, QuerySet

import itertools

from .models import Post, Ticket, Comment, Image
from .forms import TicketForm, CommentForm, CreatePostForm, SearchForm


# Create your views here.
def index(request: HttpRequest):  # Render template for url /blog/
    return render(request=request, template_name="blog/index.html")


def postList(request: HttpRequest):  # Show list of posts
    posts = Post.published.all()

    paginator = Paginator(posts, 3)
    page_number = request.GET.get("page")

    try:
        posts = paginator.page(page_number)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        posts = paginator.page(1)

    context = {"posts": posts}
    return render(request=request, template_name="blog/list.html", context=context)


def postDetail(request: HttpRequest, pk: int):  # Show detail of a post
    post = get_object_or_404(Post.published, id=pk)
    comments = post.comments.all().filter(is_active=True)
    form = CommentForm()
    context = {"post": post, "form": form, "comments": comments}
    return render(request=request, template_name="blog/detail.html", context=context)


def createTicket(request: HttpRequest):  # Create a ticket in template
    if request.method == "POST":
        form = TicketForm(request.POST)
        if not request.user.is_authenticated:
            return HttpResponse("Please register you account first!")
        if form.is_valid():
            ticket = Ticket()
            data = form.cleaned_data
            author = ticket.author = request.user
            title = ticket.title = data["title"]
            message = ticket.message = data["message"]
            subject = ticket.subject = data["subject"]

            email = ticket.email = data["email"]
            phone = ticket.phone_number = data["phone_number"]
            ticket.save()

            return redirect("blog:index")
    else:
        form = TicketForm()

    context = {"form": form}
    return render(request=request, template_name="forms/ticket.html", context=context)


def addComment(
    request: HttpRequest, pk: int
):  # Create a comment for specific post in database
    form = CommentForm(request.POST)
    if request.user.is_authenticated:
        post = get_object_or_404(Post.published, id=pk)
        comment = None
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.is_active = True
            comment.save()

            context = {"form": form, "comment": comment, "post": post}
            return redirect("blog:post_detail", pk=pk)

        comments = post.comments.all().filter(is_active=True)
        context = {"post": post, "form": form, "comments": comments}
        return render(
            request=request, template_name="blog/detail.html", context=context
        )
    else:
        return HttpResponse("<h1>Please register your account first!</h1>")


def createPost(request: HttpRequest):  # Create Post view
    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponse("Please register you account first!")
        form = CreatePostForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()

            for img in [data["image1"], data["image2"]]:
                if img:
                    Image(image_file=img, post=new_post).save()

            return redirect("blog:post_list")
    else:
        form = CreatePostForm()

    context = {"form": form}
    return render(request=request, template_name="forms/post.html", context=context)


@require_GET
def postSearch(request: HttpRequest):
    query = None
    result = []
    if request.GET.get("query"):
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]

            def search(field: str, queryset: QuerySet, precision: float) -> QuerySet:
                return queryset.annotate(
                    similarity=TrigramSimilarity(field, query)
                ).filter(similarity__gt=precision)

            post_title_result = search("title", Post.published, 0.05)
            post_description_result = search("description", Post.published, 0.05)

            post_result = (post_title_result | post_description_result).order_by(
                "-similarity"
            )

            image_title_result = search("title", Image.objects, 0.05)
            image_description_result = search("description", Image.objects, 0.05)

            image_result = (image_title_result | image_description_result).order_by(
                "-similarity"
            )
            image_result = list(map(lambda img: img.post, image_result))

            result_ = list(itertools.chain(image_result, post_result))
            result = []
            for item in result_:
                if item not in result:
                    result.append(item)

    context = {
        "query": query,
        "result": result,
    }
    return render(request=request, template_name="blog/search.html", context=context)


@login_required(login_url="admin:index")
def profile(request: HttpRequest):
    user = request.user
    posts = user.posts.order_by("-create_date")
    tickets = user.tickets.order_by("-create_date")
    context = {"user": user, "posts": posts, "tickets": tickets}

    return render(request=request, template_name="blog/profile.html", context=context)


@login_required(login_url="admin:index")
def postDelete(request: HttpRequest, pk: int):
    post = get_object_or_404(Post, id=pk)
    if request.method == "POST":
        post.delete()
        return redirect("blog:profile")

    return render(
        request=request,
        template_name="forms/delete-post.html",
    )


@login_required(login_url="admin:index")
def postEdit(request: HttpRequest, pk: int):
    post = get_object_or_404(Post, id=pk)

    if request.method == "POST":
        form = CreatePostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            data = form.cleaned_data
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()

            for img in [data["image1"], data["image2"]]:
                if img:
                    Image(image_file=img, post=new_post).save()

            return redirect("blog:profile")
    else:
        form = CreatePostForm(instance=post)

    context = {"post": post, "form": form}

    return render(
        request=request, template_name="forms/edit-post.html", context=context
    )


@require_GET
@login_required(login_url="admin:index")
def imageDelete(request: HttpRequest, pk: int):
    img = get_object_or_404(Image, id=pk)
    user = img.post.author
    
    if not user == request.user:
        return HttpResponse("You dont have access to this image!")
    
    img.delete()
    return redirect("blog:profile")
