from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)
    number = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), nullable=False)
    role = db.Column(db.String(), default='User')
    songs = db.relationship('Songs', back_populates='creator')
    albums = db.relationship('Album', back_populates='creator')


class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(), nullable=False)
    title = db.Column(db.String(), nullable=False)
    artist = db.Column(db.String(), nullable=False)
    genre = db.Column(db.String(), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    rating = db.Column(db.Integer)
    mp3 = db.Column(db.String(), nullable=False)
    lyrics = db.Column(db.String())
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=False)
    creator_id = db.Column(
        db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', back_populates='songs')

    def calculate_average_rating(self):
        total_ratings = UserRating.query.filter_by(song_id=self.id).count()
        if total_ratings == 0:
            return None
        sum_ratings = UserRating.query.with_entities(
            func.sum(UserRating.rating)).filter_by(song_id=self.id).scalar()
        return sum_ratings / total_ratings


class UserRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'))
    rating = db.Column(db.Integer, nullable=False)

    db.UniqueConstraint('user_id', 'song_id', name='unique_user_song_rating')


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('playlists', lazy=True))
    songs = db.relationship(
        'Songs', secondary='playlist_song', backref='playlists', lazy=True)


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    release_date = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False)
    creator_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', back_populates='albums', lazy=True)
    songs = db.relationship('Songs', backref='album', lazy=True)


playlist_song = db.Table('playlist_song',
                         db.Column('playlist_id', db.Integer, db.ForeignKey(
                             'playlist.id'), primary_key=True),
                         db.Column('song_id', db.Integer, db.ForeignKey(
                             'songs.id'), primary_key=True)
                         )


class View(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'))
    song = db.relationship('Songs', backref=db.backref('views', lazy=True))
