from http.client import HTTPResponse
from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView
from .models import UserInZavalinkaGame, ZavalinkaGame, Profile, ZavalinkaWord
from django.contrib.auth.models import User
from random import shuffle
from .forms import AddWordsForm

# Create your views here.


def home_page_view(request):
    return render(request, "zavalinka_game/home_page.html")


def friends_list(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('login'))
    profile = request.user.profile
    context = {"all_friends": profile.friends.all()}
    return render(request, "zavalinka_game/friends_list.html", context=context)

class ProfilePage(TemplateView):
    def get(self, request, user):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        profile_img = User.objects.get(username=user).profile.profile_pic.url
        users_profile = user == request.user.username
        friends = (User.objects.get(username=user).profile in request.user.profile.friends.all())
        context = {
            "profile_img":profile_img,
            "users_profile":users_profile,
            "user":user,
            "friends":friends,
        }
        return render(request, "zavalinka_game/profile.html", context=context)
    
    def post(self, request, user):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        if "makefriend" in request.POST:
            request.user.profile.make_friend(User.objects.get(username=user).profile)
            return HttpResponseRedirect(reverse("profile", kwargs={'user':user}))
        request.user.profile.upload_photo(request.FILES['profimg'])
        #request.user.profile.profile_img = new_image.name
        return HttpResponseRedirect(reverse("profile", kwargs={'user':user}))

class CreateGameView(TemplateView):
    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        return render(request, 'zavalinka_game/create_game.html')

    def post(self, request):
        game = ZavalinkaGame.objects.create(rounds=request.POST.get("number_of_rounds"),
                                            name=request.POST.get("name"))
        user_in_game = UserInZavalinkaGame(user=request.user.profile, game=game)
        user_in_game.save()
        return HttpResponseRedirect(reverse('game') + '?game_id=' + str(game.id))

class GameView(TemplateView):
    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        if 'game_id' not in request.POST:
            return render(request, 'zavalinka_game/join_game_error.html')
        game_id = request.POST['game_id']
        games = ZavalinkaGame.objects.filter(id=game_id)
        if games.count() != 1:
            return render(request, 'zavalinka_game/join_game_error.html')
        user = request.user
        game = games[0]
        game_phase = game.phase
        users_in_game = game.users.all()
        if game_phase == 'waiting_for_players':
            game.next_phase()
        if game_phase == 'writing_definitions':
            users_in_game.get(user=user.profile, game=game).user_answered(request.POST['definition'])
            game.user_answered()
            num_of_ans = game.status
            if num_of_ans == users_in_game.count():
                game.next_phase()
        if game_phase == 'choosing_definition':
            users_in_game.get(user=user.profile, game=game).user_chose(request.POST['definition'])
            game.user_answered()
            num_of_ans = game.status
            if num_of_ans == users_in_game.count():
                for user_in_game in users_in_game:
                    if user_in_game.last_choice == str(game.last_ask.definition):
                        user_in_game.change_score(3)
                    else:
                        for user in users_in_game.filter(last_answer=user_in_game.last_choice):
                            user.change_score(1)
                game.next_phase()
        if game_phase == 'round_results':
            game.next_phase()
        return HttpResponseRedirect(reverse('game') + '?game_id=' + str(game.id))
        

    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        if 'game_id' not in request.GET:
            return render(request, 'zavalinka_game/join_game_error.html')
        game_id = request.GET['game_id']
        games = ZavalinkaGame.objects.filter(id=game_id)
        if games.count() != 1:
            return render(request, 'zavalinka_game/join_game_error.html')
        user = request.user
        game = games[0]
        game_phase = str(game.phase)
        users_in_game = game.users.all()
        context = {
            'game': game,
            'users_in_game':users_in_game,
            'user_answered':users_in_game.get(user=user.profile).not_answered,
        }
        if game_phase == 'waiting_for_players':
            return render(request, 'zavalinka_game/game/waiting_for_players.html', context=context)
        if game_phase == 'writing_definitions':
            return render(request, 'zavalinka_game/game/writing_definitions.html', context=context)
        if game_phase == 'choosing_definition':
            definitions = [game.last_ask.definition]
            for user_in_game in users_in_game:
                definitions.append(user_in_game.last_answer)
            shuffle(definitions)
            context['definitions'] = definitions
            return render(request, 'zavalinka_game/game/choosing_definition.html', context=context)
        if game_phase == 'round_results':
            return render(request, 'zavalinka_game/game/round_results.html', context=context)
        if game_phase == 'endscreen':
            max_score = -1
            winner = None
            for user_in_game in users_in_game:
                if max_score < user_in_game.score:
                    max_score = user_in_game.score
                    winner = str(user_in_game)
            context['winner'] = winner
            return render(request, 'zavalinka_game/game/endscreen.html', context=context)


class AllGamesView(TemplateView):
    def get(self, request):
        games = ZavalinkaGame.objects.exclude(phase__exact='endscreen')
        context = {"games": [(game, {"users_str": ", ".join([str(user_in_game.user.user.username) for user_in_game in game.users.all()])}) for game in games]}
        return render(request, 'zavalinka_game/all_games.html', context=context)


class JoinGameView(TemplateView):
    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        if 'game_id' not in request.POST:
            return render(request, 'zavalinka_game/join_game_error.html')
        game_id = request.POST['game_id']
        games = ZavalinkaGame.objects.filter(id=game_id)
        if games.count() != 1:
            return render(request, 'zavalinka_game/join_game_error.html')
        user = request.user
        game = games[0]
        if not game.users.filter(user=user.profile).exists():
            user_in_game = UserInZavalinkaGame(user=user.profile, game=game)
            user_in_game.save()
        return HttpResponseRedirect(reverse('game') + '?game_id=' + str(game.id))


class AddWordsView(TemplateView):
    def get(self, request):
        if (not request.user.is_authenticated) or (not request.user.is_superuser):
            return render(request, 'zavalinka_game/add_words/not_a_super_user.html')
        context = {
            'add_words_form': AddWordsForm(),
        }
        return render(request, 'zavalinka_game/add_words/add_words.html', context=context)

    def post(self, request):
        if (not request.user.is_authenticated) or (not request.user.is_superuser):
            return render(request, 'zavalinka_game/add_words/not_a_super_user.html')
        context = {}
        form = AddWordsForm(request.POST, request.FILES)
        context['add_words_form'] = form
        if form.is_valid():
            words_file = request.FILES["words"]
            if not words_file.name.endswith(".txt"):
                context['default_shown_message'] = 'Файл должен иметь расширение .txt'
                context['default_shown_message_color'] = 'red'
            else:
                words_string = words_file.read().decode('utf-8')
                ok = True
                words_to_add = []
                for word_line in words_string.split('\n'):
                    word_and_definition = word_line.strip().split(':')
                    if len(word_and_definition) == 0 or (len(word_and_definition) == 1 and word_and_definition[0] == ''):
                        continue
                    if len(word_and_definition) != 2:
                        ok = False
                        if len(word_and_definition) == 1:
                            context['default_shown_message'] = 'Неверный формат файла: есть непустая строка без символа ":"'
                        else:
                            context['default_shown_message'] = 'Неверный формат файла: есть строка с облее чем одним символом ":"'
                        context['default_shown_message_color'] = 'red' 
                        break
                    words_to_add.append(word_and_definition)
                if ok:
                    for word, definition in words_to_add:
                        ZavalinkaWord.objects.filter(word=word).delete()
                        word_object = ZavalinkaWord(word=word, definition=definition)
                        word_object.save()
                    context['default_shown_message'] = 'Слова успешно добавлены!'
                    context['default_shown_message_color'] = 'green'

        return render(request, 'zavalinka_game/add_words/add_words.html', context=context)
