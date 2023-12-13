from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from sqlalchemy import or_, func

import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
import base64

import os
from models import db, User, Songs, Playlist, Album, playlist_song, View, UserRating


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_app.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'tempPassword'

db.init_app(app)
app.app_context().push()
db.create_all()

login_manager = LoginManager(app)
login_manager.login_view = '/'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/home')
@login_required
def root():

    user = current_user
    songs = Songs.query.all()
    playlists = Playlist.query.filter_by(user=current_user).all()
    unique_genres = [genre[0]
                     for genre in Songs.query.with_entities(Songs.genre).distinct()]

    return render_template('home.html', songs=songs, user=user, playlists=playlists, unique_genres=unique_genres)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        name, password = request.form.get(
            'name'), request.form.get('password')

        user = User.query.filter_by(username=name).first()
        if user and password == user.password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect('/home')
        else:
            return {'message': 'Wrong Username or Password'}

    else:
        return render_template('user_login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/creator', methods=['GET', 'POST'])
@login_required
def creator_login():
    if current_user.role == 'User':
        if request.method == 'POST':
            res = request.form.get('dono')
            if res == 'Get Started':
                current_user.role = 'Creator'
                db.session.commit()
                return redirect('/creator/welcome')
            else:
                return logout()

        else:
            return render_template('creator_register.html')
    else:
        return redirect('/creator-dashboard')


@app.route('/creator/welcome')
@login_required
def creator_welcome():
    return render_template('creator_welcome.html')


@app.route('/creator-dashboard')
@login_required
def creator_dashbord():
    if current_user.role == "Creator":
        recent_uploads = Songs.query.filter_by(creator=current_user).order_by(
            Songs.timestamp.desc()).limit(5).all()
        total_uploads = Songs.query.filter_by(creator=current_user).count()
        total_albums = Album.query.filter_by(creator=current_user).count()
        songs = Songs.query.filter_by(creator=current_user).all()

        if not songs:
            avg = 0.0

        total_ratings = 0
        total_rated_songs = 0

        for song in songs:
            user_rating = UserRating.query.filter_by(
                user_id=current_user.id, song_id=song.id).first()
            if user_rating:
                total_ratings += user_rating.rating
                total_rated_songs += 1

        if total_rated_songs == 0:
            avg = 0.0
        else:
            avg = total_ratings / total_rated_songs

        avg = round(avg, 2)

        return render_template('creator_dashboard.html', recent_uploads=recent_uploads, total_uploads=total_uploads, total_albums=total_albums, avg=avg)

    elif current_user.role == "User":
        return redirect("/creator")

    else:
        return {"message": "You are not a creator"}


@app.route('/user/create', methods=["GET", "POST"])
def create_user():
    if request.method == 'POST':
        name, password, number, email = request.form.get('name'), request.form.get(
            'password'), request.form.get('number'), request.form.get('email')
        if bool(User.query.filter_by(number=number).first()):
            return {'message': 'user Already exits'}
        else:
            user = User(username=name, password=password,
                        number=number, email=email)
            db.session.add(user)
            db.session.commit()
            return redirect('/home')
    else:
        return render_template('create_user.html')


@app.route('/songs/add', methods=["GET", "POST"])
@login_required
def add_song():
    if current_user.role == "Creator":
        if request.method == 'POST':
            title, artist, album, lyrics, genre = request.form.get('title'), request.form.get(
                'artist'), request.form.get('album'), request.form.get('lyrics'), request.form.get('genre')
            image = request.files['image']
            mp3_file = request.files['mp3']

            if image and mp3_file:
                image_filename = 'images/' + image.filename
                mp3_filename = 'songs/' + mp3_file.filename
                image.save(os.path.join(
                    app.config['UPLOAD_FOLDER'], image_filename))
                mp3_file.save(os.path.join(
                    app.config['UPLOAD_FOLDER'], mp3_filename))

                song = Songs(artist=artist, title=title,
                             lyrics=lyrics, album_id=album, image=image_filename, mp3=mp3_filename, genre=genre,
                             creator=current_user)
                db.session.add(song)
                db.session.commit()
                return redirect('/home')
        else:
            existing_albums = Album.query.all()
            return render_template('add_song.html', existing_albums=existing_albums)
    else:
        return redirect('/home')


@app.route('/del/song/<id>')
@login_required
def del_song(id):
    if current_user.role == "Creator":
        song = Songs.query.filter_by(id=id).first()
        db.session.delete(song)
        db.session.commit()
        return redirect('/creator-dashboard')

    elif current_user.role == "Admin":
        song = Songs.query.filter_by(id=id).first()
        db.session.delete(song)
        db.session.commit()
        return redirect('/admin/songs')
    else:
        return redirect("/home")


@app.route('/edit/song/<id>', methods=["GET", "POST"])
@login_required
async def edit_song(id):
    song = Songs.query.filter_by(id=id).first()
    album = Album.query.filter_by(id=song.album_id).first()
    albums = Album.query.all()

    if request.method == "POST":
        title, album, lyrics = request.form.get(
            'title'), request.form.get('album'), request.form.get('lyrics')

        if song.title != title and title:
            song.title = title
        if song.album_id != album and album:
            song.album_id = album
        if song.lyrics != lyrics and lyrics:
            song.lyrics = lyrics
        if 'mp3' in request.files:
            mp3_file = request.files['mp3']
            mp3_filename = 'songs/' + mp3_file.filename
            mp3_file.save(os.path.join(
                app.config['UPLOAD_FOLDER'], mp3_filename))

            song.mp3 = mp3_filename
        if 'image' in request.files:
            img = request.files['image']
            img_filename = 'images/' + img.filename
            img.save(os.path.join(
                app.config['UPLOAD_FOLDER'], img_filename))

            song.image = img_filename

        db.session.commit()
        return render_template('edit_song.html', song=song, album=album, albums=albums)

    else:
        albums = Album.query.all()
        return render_template('edit_song.html', song=song, albums=albums, album=album)


@app.route('/create/playlist', methods=['GET', 'POST'])
@login_required
def create_playlist():
    if request.method == 'POST':
        title = request.form.get('title')
        playlist = Playlist(title=title, user_id=current_user.id)
        db.session.add(playlist)

        selected_song_ids = request.form.getlist('songs')
        selected_songs = Songs.query.filter(
            Songs.id.in_(selected_song_ids)).all()

        for song in selected_songs:
            if song not in playlist.songs:
                playlist.songs.append(song)

        db.session.commit()

        return redirect('/home')

    else:
        songs = Songs.query.all()
        return render_template('create_playlist.html', songs=songs)


@app.route('/playlist/<id>', methods=["GET", "DELETE"])
@login_required
def play_playlist(id):
    playlist = Playlist.query.get_or_404(id)
    if request.method == "DELETE":
        db.session.delete(playlist)
        db.session.commit()
        return '', 204

    else:
        songs = playlist.songs
        return render_template("playlist.html", playlist=playlist, songs=songs)


@app.route('/playlist/<pid>/<sid>/')
@login_required
def remove_song(pid, sid):
    playlist = Playlist.query.filter_by(id=pid).first()
    if playlist:
        song = Songs.query.get(sid)
        if song:
            playlist.songs.remove(song)
            db.session.commit()
            return redirect(f'/playlist/{pid}')
        else:
            return jsonify({'status': 'error', 'message': 'Song not found'})
    else:
        return jsonify({'status': 'error', 'message': 'Playlist not found'})


@app.route('/album', methods=['GET', 'POST'])
@login_required
def album():
    if request.method == 'POST':
        title = request.form.get('title')
        album = Album(title=title, artist=current_user.username,
                      creator=current_user)

        db.session.add(album)
        db.session.commit()

        if request.referrer.endswith("/songs/add"):
            return redirect("/songs/add")
        else:
            return redirect("/creator-dashboard")
    else:
        return render_template('album.html')


@app.route('/play/<id>')
@login_required
def play(id):
    song = Songs.query.filter_by(id=id).first()
    record_view(id)
    return render_template('play.html', song=song)


@app.route('/rate-song/<int:song_id>', methods=['GET', 'POST'])
@login_required
def rate_song(song_id):
    song = Songs.query.get(song_id)

    if request.method == 'POST':
        rating_value = int(request.form['rating'])
        existing_rating = UserRating.query.filter_by(
            user_id=current_user.id, song_id=song.id).first()

        if existing_rating:
            existing_rating.rating = rating_value
        else:
            new_rating = UserRating(
                rating=rating_value, user_id=current_user.id, song_id=song.id)
            db.session.add(new_rating)

        db.session.commit()

    return render_template('play.html', song=song)


def record_view(song_id):
    new_view = View(song_id=song_id)
    db.session.add(new_view)
    db.session.commit()


@app.route('/admin/login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        name, password = request.form.get(
            'name'), request.form.get('password')

        admin = User.query.filter_by(username=name).first()
        if admin and password == admin.password:
            if admin.role == 'Admin':
                login_user(admin)
                return redirect('/admin')
            else:
                return {'message': 'You are not a admin'}
        else:
            return {'message': 'Wrong Username or Password'}
    else:

        return render_template('admin_login.html')


@app.route('/admin')
@login_required
def admin():
    num_users = User.query.count() - 1
    num_creators = User.query.filter_by(role='Creator').count()
    num_songs = Songs.query.count()
    num_albums = Album.query.count()
    num_views = View.query.count()
    num_genre = Songs.query.distinct(Songs.genre).count()
    songs = Songs.query.all()
    song_ratings = [(song.title, song.calculate_average_rating())
                    for song in songs]
    avg = 0
    for rating in song_ratings:
        if rating[1]:
            avg += 1

    songs = Songs.query.all()
    song_views = [(song.title, len(song.views)) for song in songs]

    matplotlib.use('Agg')
    labels, views = zip(*song_views)

    fig, ax = plt.subplots()
    ax.bar(labels, views)
    ax.set_ylabel('Number of Views')
    ax.set_title('Song Views')

    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.read()).decode('utf-8')

    plt.close()

    return render_template('admin.html', num_albums=num_albums, num_creators=num_creators, num_users=num_users, num_songs=num_songs, avg=avg, img_base64=img_base64, num_genre=num_genre, num_views=num_views)


@app.route('/admin/songs')
@login_required
def admin_song():
    if current_user.role == "Admin":
        songs = Songs.query.all()
        albums = Album.query.all()
        genres = [genre[0]
                  for genre in Songs.query.with_entities(Songs.genre).distinct()]

        return render_template('admin_songs.html', songs=songs, genres=genres)
    else:
        return redirect('/home')


@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role == "Admin":
        users = User.query.all()

        return render_template('admin_users.html', users=users)
    else:
        return redirect("/home")


@app.route('/user/<id>')
@login_required
def Users(id):
    if current_user.role == "Admin":
        user = User.query.get(id)
        db.session.delete(user)
        db.session.commit()

        return redirect("/admin/users")
    else:
        return redirect("/home")


@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '')
    results = (
        Songs.query.filter(or_(
            Songs.title.ilike(f'%{query}%'),
            Songs.artist.ilike(f'%{query}%'),
            Songs.genre.ilike(f'%{query}%'),
            Songs.album_id.in_(Album.query.filter(
                Album.title.ilike(f'%{query}%')).with_entities(Album.id))
        )).all()
    )
    return render_template('search_results.html', query=query, results=results)


if __name__ == "__main__":
    app.run(debug=True)
