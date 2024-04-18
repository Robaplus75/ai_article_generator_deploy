from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from . import models
import json
from pytube import YouTube
import assemblyai as aai
import openai
import os

@login_required(login_url='/login')
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    print("Got Request to generate Blog")
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
        
        # get yt title 
        print("Getting Title")
        title = yt_title(yt_link)

        # get transcript
        print("getting transcript")
        transcription = get_transcription(yt_link)
        if not transcription:
            return JSONResponse({'error':'Failed to get Transcript'}, status=500)

        # use openAI to generate the blog
        print("generaing blog")
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error':"Failed to generate blog article"}, status=500)

        # save blog article to database
        new_blog_article = models.BlogPost(
            user = request.user,
            youtube_title = title,
            youtube_link = yt_link,
            generated_content = blog_content
        )
        new_blog_article.save()

        # retur blog articel as a response
        return JsonResponse({'content':blog_content}, status=200)

    else:
        return JsonResponse({'error':'Invalid request method'}, status=405)

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "a171daa376b84108a3b06ed368cfefa4"
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    print(transcript.text)
    return transcript.text

def generate_blog_from_transcription(transcription):
    openai.api_key = "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"
    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog artivle: \n\n{transcription}\n\nArticle:"

    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1000
    )

    generated_content = response.choices[0].text.strip()

    return generated_content

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Incorrect username or password"
            return render(request, 'login.html', {'error_message':error_message})

    return render(request, 'login.html')

def user_signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST.get('repeatpassword')

        if not password == repeatPassword:
            error_message = "Password do not match"
            return render(request, 'signup.html', {'error_message':error_message})
        else:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error Creating Account'
                return render(request, 'signup.html', {'error_message':error_message})

    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

def blog_list(request):
    return render(request, 'all-blogs.html')

def blog_details(request, pk):
    article = models.BlogPost.objects.filter(id=pk).first()
    if request.user == article.user:
        return render(request, 'blog-details.html', {'article':article})
    else:
        return redirect('/')