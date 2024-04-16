from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse,JsonResponse
from django.urls import reverse
from .models import *

import qrcode
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from django.core.files.base import ContentFile

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.views.decorators.csrf import csrf_exempt

from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Case, When, Value, IntegerField, Sum, Count
from datetime import date
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.db.models.functions import TruncMonth
from django.contrib.auth.hashers import make_password


def calculate_queue_values():
    total_completed_value = QueueEntry.objects.filter(status='completed').count() * 10

    station_completed_values = Station.objects.annotate(
        total_completed=Sum(
            Case(
                When(queueentry__status='completed', then=Value(10)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ),
        total_drivers_served=Count(
            Case(
                When(queueentry__status='completed', then='queueentry__driver'),
                default=None,
            )
        )
    )


    return total_completed_value, station_completed_values

def calculate_total_completed_entries_per_month():

    completed_entries = QueueEntry.objects.filter(status='completed')

    monthly_totals = {}

    for entry in completed_entries:
        month = entry.created.month
        if month not in monthly_totals:
            monthly_totals[month] = 0
        monthly_totals[month] += 1

    result = [{'month': month, 'total_entries': total * 10} for month, total in monthly_totals.items()]
    
    result = sorted(result, key=lambda x: x['month'])

    return result

def login_page(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_staff:
                # Admin or superadmin login
            
                messages.error(request, 'Invalid login credentials')
                return redirect('logout')  # Redirect to the Django admin index page
            else:
                # Regular user login
                stations = Station.objects.filter(station_manager=user)

                if stations.exists():
                    station = stations.first()
                    return redirect('station_page', station_id=station.id)
                else:
                    # Regular user without a station, log them out
                    logout(request)
                    messages.error(request, 'Logged out.! User does not have a station.')
                    return redirect('home')  # Redirect to home or another view for regular users
        else:
            messages.error(request, 'Invalid login credentials')

    return render(request, 'base/authentication/login.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_staff:
                # Admin or superadmin login
                return redirect('dashboard')  # Redirect to the Django admin index page
            else:

                messages.error(request, 'Invalid login credentials')
                return redirect('logout')
        else:
            messages.error(request, 'Invalid login credentials')

    return render(request, 'base/authentication/login_admin.html')


@login_required
def station(request, station_id):
    station = get_object_or_404(Station, id=station_id)

    current_date = timezone.now().date()
    q_history = QueueEntry.objects.filter(station = station )
    queue_entries = QueueEntry.objects.filter(created=current_date, station = station )
    
    context = {
        'current_date': current_date,
        'station': station,
        'queue_entries': queue_entries,
        'q_history': q_history,
    }
    return render(request, 'base/station.html', context)



def display_page(request):

    # Fetch stations and corresponding QueueEntries with status 'serving'
    stations = Station.objects.all()
    serving_queues = QueueEntry.objects.filter(status='serving')

    waiting_queues = QueueEntry.objects.filter(status='waiting')

    context = {
        'stations': stations, 
        'serving_queues': serving_queues,
        'waiting_queues': waiting_queues,
    }

    return render(request, 'base/display.html', context)

def process_next_queue(request, station_id):
    # Assuming you have a Station model with an 'id' field
    station = get_object_or_404(Station, id=station_id)

    try:
        # Find the currently serving queue for the station
        serving_queue = QueueEntry.objects.get(station=station, status='serving')

        # Set the currently serving queue to 'completed'
        serving_queue.status = 'completed'
        serving_queue.save()

        # Find the next waiting queue for the station
        next_waiting_queue = QueueEntry.objects.filter(station=station, status='waiting').first()

        if next_waiting_queue:
            # Set the next waiting queue to 'serving'
            next_waiting_queue.status = 'serving'
            next_waiting_queue.save()

        return redirect('display_page')
    except QueueEntry.DoesNotExist:
        # Handle the case where there is no currently serving queue
        return redirect('display_page')  # or return an appropriate response
    except Exception as e:
        # Handle other exceptions if necessary
        return redirect('display_page')
    

def driver_display_page(request):
    # Fetch stations and corresponding QueueEntries with status 'serving'
    stations = Station.objects.all()
    serving_queues = QueueEntry.objects.filter(status='serving')

    waiting_queues = QueueEntry.objects.filter(status='waiting')

    context = {
        'stations': stations, 
        'serving_queues': serving_queues,
        'waiting_queues': waiting_queues,
    }

    return render(request, 'base/driver_display.html', context)

def update_queue_status(request, token_number):
    queue_entry = get_object_or_404(QueueEntry, token_number=token_number)

    try:
        # Update the status to 'serving'
        queue_entry.status = 'completed'
        queue_entry.save()

        # Return a JSON response with the updated queue information
        response_data = {
            'status': 'success',
            'message': f'Queue with token {token_number} is now serving.',
            'updated_queue': {
                'token_number': queue_entry.token_number,
                'driver': f'{queue_entry.driver.first_name} {queue_entry.driver.last_name}',
            }
        }

        return JsonResponse(response_data)
    except Exception as e:
        response_data = {
            'status': 'error',
            'message': str(e),
        }
        return JsonResponse(response_data, status=500)
    
@login_required
def q_history(request):
    q_history = QueueEntry.objects.all()

    context = {
        'q_history': q_history,
    }
    return render(request, 'base/q_history.html', context)

@login_required
def dashboard(request):
    today = date.today()

    # Filter QueueEntry instances with the status of 'completed' and entry time today
    completed_entries_count = QueueEntry.objects.filter(status='completed', entry_time__date=today).count()

    # Multiply the count by 10
    total_amount = completed_entries_count * 10

    # Calculate queue values
    q = QueueEntry.objects.all()
    stations = Station.objects.all()
    drivers = JeepneyDriver.objects.all()

    total_completed_value, station_completed_values = calculate_queue_values()
    data = calculate_total_completed_entries_per_month()

    context = {
        'history': q,
        'stations': stations,
        'drivers': drivers,
        'total_completed_value': total_completed_value,
        'station_completed_values': station_completed_values,
        'completed_entries_count': completed_entries_count,
        'total_amount': total_amount,
        'data': data,
    }
    return render(request, 'base/dashboard2.html', context)

@login_required
def station_list(request):
    stations = Station.objects.all()

    available_stations = stations.filter(station_manager__isnull=True, routes__isnull=True)

    users = User.objects.all()

    available_users = users.exclude(station__isnull=False)

    routes = Route.objects.all()

    available_routes = routes.exclude(stations__isnull=False)

    context = {
        'stations': stations,
        'available_stations': available_stations,
        'available_users': available_users,
        'available_routes': available_routes,
    }


    return render(request, 'base/station_list.html', context)

@login_required
def create_station_and_route(request):
    if request.method == 'POST':
        station_name = request.POST.get('station_name')
        station_manager_id = request.POST.get('station_manager')
        route_id = request.POST.get('route')

        # Check if a station with the same name already exists
        if Station.objects.filter(name=station_name).exists():
            return JsonResponse({'success': False, 'message': 'Station with this name already exists.'})

        # Create Station object
        station = Station(name=station_name)

        # Save the station_manager if provided
        if station_manager_id:
            station_manager = User.objects.get(pk=station_manager_id)
            station.station_manager = station_manager

        # Save the station first to get an ID
        station.save()

        # Get the Route object
        route = Route.objects.get(id=route_id)

        # Save the route, then add the station to it
        route.save()
        route.stations.add(station)

        return JsonResponse({'success': True, 'message': 'Station and route created successfully.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

def edit_station(request, station_id):
    station = get_object_or_404(Station, id=station_id)

    if request.method == 'POST':
        station_name = request.POST.get('station_name')
        station_manager_id = request.POST.get('station_manager')
        route_id = request.POST.get('route')

        if Station.objects.filter(name=station_name).exclude(id=station_id).exists():
            return JsonResponse({'success': False, 'message': 'Station with this name already exists.'})

        station.name = station_name

        if station_manager_id:
            station_manager = User.objects.get(pk=station_manager_id)
            station.station_manager = station_manager
        else:
            station.station_manager = None

        station.save()

        route = Route.objects.get(id=route_id)

        route.stations.add(station)

        return JsonResponse({'success': True, 'message': 'Station updated successfully.'})

    available_users = User.objects.exclude(station__isnull=False)
    available_routes = Route.objects.exclude(stations__isnull=False)

    context = {
        'station': station,
        'available_users': available_users,
        'available_routes': available_routes,
    }

    return render(request, 'base/station_list.html', context)


def delete_station(request, station_id):
    try:
        station = Station.objects.get(id=station_id)
        station.delete()
        return JsonResponse({'success': True, 'message': 'Station deleted successfully.'})
    except Station.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Station not found.'})


@login_required
def station_history(request, pk):
    station = get_object_or_404(Station, pk=pk)
    q_history = QueueEntry.objects.filter(station=station)

    context = {
        'station': station,
        'q_history': q_history,
    }
    return render(request, 'base/station_history.html', context)

@login_required
def drivers2(request):
    routes = Route.objects.all()
    drivers = JeepneyDriver.objects.all()
    context = {
        'drivers': drivers,
        'routes': routes,
    }
    return render(request, 'base/drivers2.html', context)



def add_driver(request):
    if request.method == "POST":
        # Retrieve data from the form
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        date_of_birth = request.POST.get("date_of_birth")
        address = request.POST.get("address")
        contact_number = request.POST.get("contact")
        id_route = request.POST.get("route")

        route = Route.objects.get(id=id_route)

        # Retrieve the uploaded photo
        photo = request.FILES.get("avatar")

        # Create a JeepneyDriver object
        driver = JeepneyDriver(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            address=address,
            contact_number=contact_number,
            route=route,
            photo=photo
        )

        driver.save()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(driver.id)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image
        qr_code_buffer = BytesIO()
        qr_img.save(qr_code_buffer, format="PNG")
        driver.qr_code.save(f"{driver.id}_qr.png", ContentFile(qr_code_buffer.getvalue()))
        driver.save()

        data = {
            'success': "Driver added successfully",
            'id': driver.id,
            'qr': driver.qr_code.url,
            'name': driver.first_name + ' ' + driver.last_name,
            'route': str(driver.route),
        }
        # Return a JSON response on success
        return JsonResponse(data)

def edit_driver(request):
    if request.method == 'POST':
        # Retrieve the data from the form
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        date_of_birth = request.POST.get('date_of_birth')
        contact_number = request.POST.get('contact')
        address = request.POST.get('address')
        route_id = request.POST.get('route')

        # Retrieve the existing driver record
        driver_id = request.POST.get('driver_id')  # Make sure you have a hidden input field in your form for driver_id
        try:
            driver = JeepneyDriver.objects.get(id=driver_id)
        except JeepneyDriver.DoesNotExist:
            return JsonResponse({'error': 'Driver not found'}, status=404)

        # Update the fields
        driver.first_name = first_name
        driver.last_name = last_name
        driver.date_of_birth = date_of_birth
        driver.contact_number = contact_number
        driver.address = address
        driver.route_id = route_id  # Assuming your model has a field named route_id

        # Update the photo only if a new one is provided
        if 'avatar' in request.FILES:
            driver.photo = request.FILES['avatar']

        # Save the changes
        driver.save()

        # Redirect to a success page or any other desired page
        return redirect('drivers')

def delete_driver(request, driver_id):
    # Retrieve the driver object
    driver = get_object_or_404(JeepneyDriver, id=driver_id)

    # Perform the deletion
    driver.delete()

    # Redirect to a success page or any other desired page
    return redirect('drivers')


def driver_info2(request, driver_id):
    try:
        driver = JeepneyDriver.objects.get(id=driver_id)
        data = {
            'id': driver.id,
            'name': driver.first_name + ' ' + driver.last_name,
            'photo': driver.photo.url,
            'route': {
                'id': str(driver.route),
            },
            'qr': driver.qr_code.url
            # Add other fields as needed
        }
        return JsonResponse(data)
    except JeepneyDriver.DoesNotExist:
        return JsonResponse({'error': 'Driver not found'}, status=404)
    

def driver_info(request, driver_id):
    try:
        driver = JeepneyDriver.objects.get(id=driver_id)
        data = {
            'id': driver.id,
            'name': driver.first_name + ' ' + driver.last_name,
            'first_name': driver.first_name,
            'last_name': driver.last_name,
            'date_of_birth': driver.date_of_birth.isoformat(),
            'address': driver.address,
            'contact_number': driver.contact_number,
            'route': {
                'id': str(driver.route.id),
                'name': str(driver.route)
            },
            'photo': driver.photo.url,
            'qr': driver.qr_code.url
            # Add other fields as needed
        }
        return JsonResponse(data, encoder=DjangoJSONEncoder)
    except JeepneyDriver.DoesNotExist:
        return JsonResponse({'error': 'Driver not found'}, status=404)
    


def q_page(request):
    return render(request, 'base/q_page.html')

@login_required
def station_page(request, station_id):
    # Get the station object based on station_id or return a 404 page if not found
    station = get_object_or_404(Station, id=station_id)

    current_date = timezone.now().date()
    queue_entries = QueueEntry.objects.filter(created=current_date, station = station)
    
    context = {
        'station': station,
        'queue_entries': queue_entries,
    }
    return render(request, 'base/station_page.html', context)

def register_page(request):
    return render(request, 'base/login_register.html')

def logout_user(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    context = {
        'segment': 'home',
    }
    return render(request, 'base/home.html', context)


@login_required
def drivers(request):

    drivers = JeepneyDriver.objects.all()
    context = {
        'drivers': drivers,
        'segment': 'drivers',
    }
    return render(request, 'base/drivers.html', context)


def register_driver(request):
    if request.method == "POST":
        # Retrieve data from the form
        first_name = request.POST.get("firstname")
        last_name = request.POST.get("lastname")
        date_of_birth = request.POST.get("birthday")
        address = request.POST.get("address")
        contact_number = request.POST.get("contact_number")
        route = request.POST.get("route")

        # Retrieve the uploaded photo
        photo = request.FILES.get("photo")

        # Create a JeepneyDriver object
        driver = JeepneyDriver(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            address=address,
            contact_number=contact_number,
            route=route,
            photo=photo
        )

        driver.save()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(driver.id)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image
        qr_code_buffer = BytesIO()
        qr_img.save(qr_code_buffer, format="PNG")
        driver.qr_code.save(f"{driver.id}_qr.png", ContentFile(qr_code_buffer.getvalue()))
        driver.save()

        return HttpResponse('success') 
 
    
def add_to_queue2(request, driver_id):
    try:
        station = Station.objects.get(station_manager=request.user)
        driver = JeepneyDriver.objects.get(id=driver_id)

        # Create a new QueueEntry object
        queue_entry = QueueEntry(
            driver=driver,
            station=station,
            status = 'waiting',
        )
        queue_entry.save()

        data = {
            'success': 'Driver added to the queue',
            'token_number': queue_entry.token_number,
            'driver_name': f"{driver.first_name} {driver.last_name}",
            'route': str(station.routes.first())
        }

        return JsonResponse(data)
    except JeepneyDriver.DoesNotExist:
        return JsonResponse({'error': 'Driver not found'}, status=404)
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    


def add_to_queue(request, driver_id):
    try:
        # Get the station managed by the current user
        station = Station.objects.get(station_manager=request.user)

        # Get the driver with the specified ID
        driver = JeepneyDriver.objects.get(id=driver_id)

        # Check if the driver's route is associated with the station
        if driver.route in station.routes.all():
            # Get the first entry for today at the current station
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_entries = QueueEntry.objects.filter(station=station, created__gte=today_start)

            if today_entries.exists():
                # If there are entries for today, set the status accordingly
                first_entry = today_entries.earliest('created')
                status = 'waiting' if first_entry.status == 'serving' else 'waiting'
            else:
                # If no entries for today, set the status to 'serving'
                status = 'serving'

            # Create a new QueueEntry object
            queue_entry = QueueEntry(
                driver=driver,
                station=station,
                status=status,
            )
            queue_entry.save()

            data = {
                'success': 'Driver added to the queue',
                'token_number': queue_entry.token_number,
                'driver_name': f"{driver.first_name} {driver.last_name}",
                'route': str(station.routes.first())
            }

            return JsonResponse(data)
        else:
            print('Driver route not associated with the station')
            return JsonResponse({'error': 'Driver route not associated with the station'}, status=400)

    except JeepneyDriver.DoesNotExist:
        return JsonResponse({'error': 'Driver not found'}, status=404)
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    




@login_required
def users_page(request):
    users = User.objects.all()
    context = {
        'users': users,
    }

    return render(request, 'base/users.html', context)

def create_user_account(request):
    if request.method == 'POST':
        # Retrieve form data from POST request
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Check if passwords match
        if password1 != password2:
            return HttpResponse("Passwords do not match")

        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            return HttpResponse("Username is already taken")

        # Create a new user with the provided information
        user = User(username=username, email=email, password=make_password(password1))
        user.save()

        return redirect('users_page')

    return render(request, 'base/users.html')