from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
from pytubefix import YouTube
import os
import assemblyai as aai
import openai
from .models import BlogPost

# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent!'}, status=400)
        
        # get yt link

        title = yt_title(yt_link)

        # get transcript

        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': "Failed to get transcript"}, status=500)

        # use OpenAI to generate the blog

        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)
        
        # save blog article to database

        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_tilte=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )
        new_blog_article.save()

        # return blog article as a response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method!'}, status=405)
    
def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.get_audio_only()
    out_file = video.download(mp3=True, output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file
    
def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "1ade07020d8a4457806bcbc2bab39f00"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    
    return transcript.text

def generate_blog_from_transcription(transcription):
    client = openai.OpenAI(
        api_key="57b39b3e414e402591b8e26b39381426",
        base_url="https://api.aimlapi.com",
    )

    prompt = f"Based on the following transcript from a Youtube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"
    system_content = "You are an AI assistant who knows everything."

    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=128,
    )

    generated_content = chat_completion.choices[0].message.content

    return generated_content

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid Username Or Password"
            return render(request, 'login.html', {'error_message': error_message})
    return render(request, 'login.html')

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, "blog-details.html", {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error Creating Account'
                return render(request, 'signup.html', {'error_message': error_message})

        else:
            error_message = 'Password Dont Matched'
            return render(request, 'signup.html', {'error_message': error_message})


    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')