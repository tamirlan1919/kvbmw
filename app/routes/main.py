import logging
import re
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.forms.registration_form import RegistrationForm
from app.services.registration_service import process_registration, check_user_in_table
from app.database.engine import db
from app.database.models import CommunityLink
from sqlalchemy.exc import DatabaseError
import requests

main_bp = Blueprint('main', __name__)

# Ключи: нормализованные названия районов. Значения: ключевые слова для сопоставления.
ALLOWED_DISTRICTS = {
    'Карабудахкентский район': {
        'keywords': ['карабудахкент'],
        'localities': [
            "карабудахкент", "аданак", "гулни", "параул", "учкент",
            "какамахи", "манасаул", "нижнее казанище", "верхнее казанище"
        ]
    },
    'Левашинский район': {
        'keywords': ['леваши'],
        'localities': [
            "леваши", "ашты", "какамахи", "цухта", "цудахар",
            "муги", "хуршни", "уркарах", "куппа"
        ]
    },
    'Избербаш + Каякентский район': {
        'keywords': ['избербаш', 'каякент'],
        'localities': [
            "избербаш", "наякент", "новокаякент", "первомайское",
            "узнимахи", "алхаджакент", "дарваг", "джанга"
        ]
    },
    'Сергокалинский район': {
        'keywords': ['сергокала', 'сергокалинский'],
        'localities': [
            "сергокала", "деличобан", "мулебки", "кичи-гамри",
            "аялизимахи", "нижнее мулебки", "картас-махи"
        ]
    }
}

def normalize_district_name(location):
    if not location:
        return None
    
    location = location.lower().strip()
    
    location = re.sub(
        r'(городской округ|муниципальный район|район|муниципальное образование)\s*', 
        '', 
        location, 
        flags=re.IGNORECASE
    ).strip()
    
    # Обработка комбинированного района
    if 'избербаш' in location:
        return 'Избербаш + Каякентский район'
    
    for district, data in ALLOWED_DISTRICTS.items():
        for keyword in data['keywords']:
            if keyword in location:
                return district
    return None

def is_location_allowed(location, district):
    normalized_district = normalize_district_name(district) if district else None
    
    # Проверяем, что район разрешен
    if not normalized_district:
        return False
    
    # Проверяем, что населенный пункт есть в списке для района
    return location.lower() in [loc.lower() for loc in ALLOWED_DISTRICTS[normalized_district]['localities']]

def is_district_allowed(district):
    normalized_district = normalize_district_name(district)
    return normalized_district in ALLOWED_DISTRICTS

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    form = RegistrationForm()
    is_registered = None
    community_link = None
    
    try:
        if form.validate_on_submit():
            if not form.latitude.data or not form.longitude.data:
                flash("Не удалось определить ваше местоположение. Включите геолокацию!", "error")
                return render_template('index.html', form=form, is_registered=is_registered, community_link=community_link)
                
            address = get_full_address_by_coordinates(form.latitude.data, form.longitude.data)
            if not address:
                flash("Ошибка проверки адреса. Попробуйте позже.", "error")
                return render_template('index.html', form=form, is_registered=is_registered, community_link=community_link)

            district = address.get('county', '')
            
            if not is_district_allowed(district):
                flash(f"Регистрация недоступна для вашего района ({district})!", "error")
                return render_template('index.html', form=form, is_registered=is_registered, community_link=community_link)

            selected_district = form.district.data
            normalized_geo = normalize_district_name(district)
            
            # Проверка соответствия районов
            if selected_district != normalized_geo:
                # Специальная проверка для комбинированного района
                if selected_district == 'Избербаш + Каякентский район':
                    if normalized_geo not in ['Избербаш + Каякентский район', 'Каякентский район']:
                        flash("Выбранный район не соответствует геолокации!", "error")
                        return render_template('index.html', form=form, is_registered=is_registered, community_link=community_link)
                else:
                    flash("Выбранный район не соответствует геолокации!", "error")
                    return render_template('index.html', form=form, is_registered=is_registered, community_link=community_link)

            # Получаем ссылку на сообщество
            community_link_obj = CommunityLink.query.filter_by(district=selected_district).first()
            community_link = community_link_obj.link if community_link_obj else '#'
            
            # Сохраняем данные
            if check_user_in_table(form.phone.data):
                is_registered = '#alreadyRegisteredModal'
            else:
                process_registration(
                    form=form,
                    district=selected_district,
                    city=extract_locality_from_address(address),
                    region=address.get('state', 'Дагестан'),
                    country=address.get('country', 'Россия')
                )
                is_registered = '#registrationSuccessModal'
                
    except DatabaseError as e:
        logging.error(f"Ошибка базы данных: {e}")
        flash("Ошибка подключения к базе данных. Пожалуйста, попробуйте снова.", "error")
    except Exception as e:
        logging.error(f"Общая ошибка при обработке формы: {e}")
        flash("Ошибка сервера. Попробуйте позже.", "error")

    return render_template('index.html', form=form, is_registered=is_registered, community_link=community_link)

def get_full_address_by_coordinates(latitude, longitude):
    
    url = f'https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&addressdetails=1'
    print(url)
    headers = {'User-Agent': 'RaffleApp/1.0 tchinchaev@bk.ru'}
    try:
        response = requests.get(url, headers=headers)
        return response.json().get('address') if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса к Nominatim: {e}")
        return None

def extract_locality_from_address(address):
    fields = ['village', 'town', 'city', 'suburb', 'municipality']
    for field in fields:
        if address.get(field):
            return address[field]
    return address.get('county', '')
