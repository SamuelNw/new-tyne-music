from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as __
from django.core.exceptions import ValidationError

from core.models import Profile


def upload_artist_image(instance: 'Artist', filename: str):
    return f'dy/music/artists/{instance.pk}/{filename}'


def upload_creator_image(instance: 'Creator', filename: str):
    return f'dy/music/creators/{instance.pk}/{filename}'


def upload_genre_image(instance: 'Genre', filename: str):
    return f'dy/music/creators/{instance.pk}/{filename}'


def upload_album_image(instance: 'Album', filename: str):
    return f'dy/music/albums/{instance.pk}/{filename}'


def upload_song_file(instance: 'Song', filename: str):
    return f'dy/music/albums/{instance.album.pk}/{instance.pk}/{filename}'


def upload_playlist_image(instance: 'Playlist', filename: str):
    if instance.profile:
        abs_path = f'users/{instance.profile.user.pk}/{instance.profile.pk}/{instance.pk}/{filename}'
    elif instance.creator:
        abs_path = f'creator/{instance.creator.pk}/{instance.pk}/{filename}'
    else:
        abs_path = f'blank/{instance.pk}/{filename}'

    return f'dy/music/playlists/{abs_path}'


class Artist(models.Model):
    name = models.CharField(max_length=100)
    is_group = models.BooleanField(default=False)
    group_members = models.ManyToManyField('self')
    avi = models.ImageField(default='/defaults/artist.png', upload_to=upload_artist_image)
    cover = models.ImageField(default='/defaults/artist_large.png', upload_to=upload_artist_image)
    bio = models.TextField(blank=True, null=True)
    nicknames = models.TextField(blank=True, null=True, help_text='Comma separated names the artist goes by')
    objects = models.Manager()

    def add_artist_to_group(self, artist: 'Artist'):
        if self.is_group and type(artist) == type(self) and not artist.is_group:
            self.group_members.add(artist)

    def __str__(self):
        _type_ = 'Group' if self.is_group else 'Artist'
        return f'<{_type_} \'{self.name}\'>'


class Genre(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    avi = models.ImageField(default='/defaults/genre.png', upload_to=upload_genre_image)
    cover = models.ImageField(default='/defaults/genre_wide.png', upload_to=upload_genre_image)
    objects = models.Manager()

    def __str__(self):
        return f'<Genre: \'{self.title}\'>'

    def __repr__(self):
        return self.__str__()


class Creator(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    avi = models.ImageField(default='/defaults/creator.png', upload_to=upload_creator_image)
    cover = models.ImageField(default='/defaults/creator_wide.png', upload_to=upload_creator_image)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    genres = models.ManyToManyField(Genre, blank=True)
    objects = models.Manager()

    def add_creator_user(self, user):
        if hasattr(user, 'is_staff') and user.is_staff:
            self.users.add(user)

    def __str__(self):
        return f'<TyneMusicContentCreator: \'{self.name}\'>'

    def __repr__(self):
        return self.__str__()


class Album(models.Model):
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    date_of_release = models.DateField()
    is_single = models.BooleanField(default=False)
    is_ep = models.BooleanField(default=False)
    cover = models.ImageField(default='/defaults/album.png', upload_to=upload_album_image)
    likes = models.IntegerField(default=0, null=True, blank=True)
    copyright = models.TextField(blank=True, null=True)
    artists = models.ManyToManyField(Artist, blank=True)
    other_versions = models.ManyToManyField('self', blank=True)
    objects = models.Manager()

    @property
    def album_type(self):
        t = 'Long Play'
        if self.is_ep:
            t = 'Extended Play'
        elif self.is_single:
            t = 'Single'

        return t

    def add_sister_album(self, album):
        if type(album) == type(self) and self.pk:
            self.other_versions.add(album)

    def clean(self):
        if self.is_single and self.is_ep:
            raise ValidationError(__('EP or Single not both'))

        return super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        name = 'Album'
        if self.is_ep:
            name = 'EP'
        elif self.is_single:
            name = 'Single'

        return f'<{name}: \'{self.title}\'>'


class Song(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    track_no = models.IntegerField()
    title = models.CharField(max_length=200)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    explicit = models.BooleanField(default=False)
    length = models.IntegerField(default=0, help_text='Length of the song in seconds')
    file = models.FileField(blank=True, null=True, upload_to=upload_song_file)
    likes = models.IntegerField(default=0, blank=True, null=True)
    additional_artists = models.ManyToManyField(Artist, blank=True)
    streams = models.IntegerField(default=0, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        unique_together = (('album', 'track_no'),)

    @property
    def length_string(self):
        length = '0:00'
        if self.pk and self.length:
            length = f'{self.length // 60}:{self.length % 60}'
        return length

    def add_additional_artist(self, artist):
        if self.pk and type(artist) == Artist and artist not in self.album.artists.all():
            self.additional_artists.add(artist)

    def __str__(self):
        return f'<Song: \'{self.title}\' from \'{self.album.title}\'>'


class Playlist(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, blank=True, null=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    songs = models.ManyToManyField(Song, blank=True)
    songs_order = models.TextField(
        help_text='Comma separated digits indicating a pk for each song',
        blank=True,
        null=True,
        default=''
    )
    likes = models.IntegerField(default=0)
    cover = models.ImageField(default='/defaults/playlist.png', upload_to=upload_playlist_image)
    cover_wide = models.ImageField(default='/defaults/playlist_wide.png', upload_to=upload_playlist_image)
    timely_cover = models.ImageField(upload_to=upload_playlist_image, blank=True, null=True)
    timely_cover_wide = models.ImageField(upload_to=upload_playlist_image, blank=True, null=True)
    objects = models.Manager()

    @property
    def songs_order_pk(self):
        order = []
        if self.pk:
            if self.songs_order:
                order = self.songs_order.split(',')
        return [int(pk) for pk in order if pk.isdigit()]

    def og_order(self):
        for song in self.songs.all():
            self.set_song_order(song.pk, position=-1)

    def verify_songs_and_songs_order(self):
        verification = True
        songs = [song.pk for song in self.songs.all()]
        songs_order = self.songs_order_pk

        if len(songs) != len(songs_order):
            verification = False
        else:
            if sorted(songs) != sorted(songs_order):
                verification = False

        return verification

    def songs_by_order(self):
        order = self.songs_order_pk
        all_songs = self.songs.all()
        songs = list(range(len(order)))

        if self.verify_songs_and_songs_order():
            songs = [all_songs.get(pk=pk) for pk in order]

        return songs

    def set_song_order(self, pk: int, position: int):
        if self.pk:
            order_x = self.songs_order_pk

            if position < 0:
                position = len(order_x)

            if position > len(order_x):
                position = len(order_x)

            if pk in order_x:
                order_x.remove(pk)

            order_x.insert(position, pk)
            self.songs_order = ','.join([str(pk) for pk in order_x])
            self.save()

    def clean(self):
        if self.creator and self.profile:
            raise ValidationError(__('Playlist is by either Profile or Creator'))
        return super().clean()

    def add_song_to_playlist(self, song, position=-1):
        if self.pk and type(song) == Song and type(position) == int:
            if song not in self.songs.all():
                self.songs.add(song)
                self.set_song_order(song.pk, position)

    def save(self, *args, **kwargs):
        self.clean()
        return super().save()

    def owner(self):
        owner = ''

        if self.profile:
            owner = self.profile.name

        if self.creator:
            owner = self.creator.name

        return owner

    def __str__(self):
        name = 'Playlist'

        if self.profile:
            name = 'UserPlaylist'

        if self.creator:
            name = 'CreatorPlaylist'

        return f'<{name} \'{self.title}\' by \'{self.owner()}\'>'


class CreatorSection(models.Model):
    name = models.CharField(max_length=2000)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    artists = models.ManyToManyField(Artist, blank=True)
    albums = models.ManyToManyField(Album, blank=True)
    playlists = models.ManyToManyField(Playlist, blank=True)
    objects = models.Manager()

    def __str__(self):
        return f'<CreatorSection from \'{self.creator.name}\'>'
