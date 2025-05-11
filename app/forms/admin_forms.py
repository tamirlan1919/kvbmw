from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import DataRequired, URL

# Обновленные районы
DISTRICT_CHOICES = [
    ('Карабудахкентский район', 'Карабудахкентский район'),
    ('Левашинский район', 'Левашинский район'),
    ('Избербаш + Каякентский район', 'Избербаш + Каякентский район'),
    ('Сергокалинский район', 'Сергокалинский район')
]

class CommunityLinkForm(FlaskForm):
    district = SelectField('Район', validators=[DataRequired()], choices=DISTRICT_CHOICES)
    link     = StringField('Ссылка на сообщество', validators=[DataRequired(), URL()])
