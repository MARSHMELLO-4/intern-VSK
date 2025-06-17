from django.shortcuts import render,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from .models import Lead, category ,CustomUser # Ensure Lead and category models are imported
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User 
import json
from .forms import CustomUserCreationForm
def loginSalesman(request):
    page = 'login'
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try: 
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(request, "User does not exist")
            return render(request, 'salesmanPortal/loginSalesmen.html', {'page': page})

        # Authenticate using email instead of username
        user = authenticate(request, username=user.username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('salesmanDashboard')
        else:
            messages.error(request, "Incorrect password")

    return render(request, 'salesmanPortal/loginSalesmen.html', {'page': page})

from .forms import CustomUserCreationForm

def registerUser(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful!')
            return redirect('loginSalesman')  # Redirect to login page after successful registration
        else:
            # Print form errors to console for debugging
            print(form.errors)
            messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'salesmanPortal/salesmanRegister.html', {'form': form}) # Render the registration template with the form

def salesmanDashboard(request):
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated
    lead = Lead.objects.filter(assigned_to=request.user)  # Get leads assigned to the logged-in user
    total_leads = lead.count()  # Count the total number of leads assigned to the user
    context = {
        'leads': lead,  # Pass the leads to the template
        'total_leads': total_leads,  # Pass the total leads count to the template
    }
    return render(request, 'salesmanPortal/salesmanDashboard.html', context)  # Render the dashboard template

def loginAdmin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            messages.error(request, "Admin user does not exist")
            return render(request, 'salesmanPortal/loginAdmin.html')

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('viewCategory')  # Redirect to admin dashboard after login
        else:
            messages.error(request, "Invalid admin credentials")
    return render(request, 'salesmanPortal/loginAdmin.html')  # Render the admin login template

from django.db.models import F

def adminDashboard(request, category_id=None):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginAdmin')

    # Get leads that were actually updated after creation
    leads = Lead.objects.exclude(updated_at=F('created_at')).order_by('-updated_at')
    
    # Apply category filter if specified
    if category_id:
        leads = leads.filter(category_id=category_id)
    else:
        leads = leads.filter(category__isnull=False)
    
    # Count statistics
    total_leads = leads.count()
    
    # Get non-staff users (salesmen) using CustomUser
    total_salesmen = CustomUser.objects.filter(is_staff=False).count()
    
    # Get all users (using CustomUser)
    users = CustomUser.objects.all()
    
    # Status counts - optimized to use the same base queryset when possible
    status_filters = {
        'new_leads': 'New',
        'contacted_leads': 'Contacted',
        'in_discussion_leads': 'In Discussion',
        'not_interested_leads': 'Not Interested',
        'converted_leads': 'Converted'
    }
    
    status_counts = {}
    for key, status in status_filters.items():
        if category_id:
            status_counts[key] = Lead.objects.filter(
                status=status,
                category_id=category_id
            ).count()
        else:
            status_counts[key] = Lead.objects.filter(status=status).count()
    
    # Get the selected category if specified
    selected_category = None
    if category_id:
        selected_category = category.objects.filter(id=category_id).first()
    
    context = {
        'total_leads': total_leads,
        'total_salesmen': total_salesmen,
        'leads': leads,
        'users': users,
        'selected_category': selected_category,
        'category_id': category_id,
        **status_counts  # Unpack all status counts into the context
    }
    
    return render(request, 'salesmanPortal/adminDashboard.html', context)


import pandas as pd
from datetime import datetime
from .models import Lead  # Ensure Lead model is imported

def uploadLeads(request,category_id=None):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginAdmin')
    selected_category = None
    if category_id:
        try:
            selected_category = category.objects.get(id=category_id)
        except category.DoesNotExist:
            messages.error(request, "Category does not exist")
            return redirect('adminDashboard')
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file, header=None)  # No header in file
        for _, row in df.iterrows():
            try:
                name = row[4]
                email = row[6]

                if pd.isna(name) or pd.isna(email):
                    print(f"Skipping row due to missing required fields: {row.values}")
                    continue

                Lead.objects.create(
                    name=name,
                    email=email,
                    phone=row[5] if not pd.isna(row[5]) else '',
                    city=row[1] if not pd.isna(row[1]) else '',
                    company=row[0] if not pd.isna(row[0]) else '',
                    status='New',
                    priority='Warm',
                    interest='',
                    role='',
                    notes='',
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    category=selected_category  # Assuming category is not provided in the file
                )
            except Exception as e:
                print(f"Error saving row {row.values}: {e}")

        # ✅ Move redirect here, after the loop
        return redirect('adminDashboard', category_id=category_id)
    context = {
        'category_id': category_id,  # Pass the category ID to the template
        'selected_category': selected_category,  # Pass the selected category to the template
    }
    return render(request, 'salesmanPortal/assignLeads.html', context)



@csrf_exempt  # Consider using @require_POST with proper CSRF protection in production
def assign_lead_ajax(request):
    if request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            lead_id = data.get("lead_id")
            user_id = data.get("user_id")

            if not lead_id or not user_id:
                return JsonResponse({
                    "success": False,
                    "error": "Missing lead_id or user_id"
                }, status=400)

            # Get objects with error handling
            try:
                lead = Lead.objects.get(id=lead_id)
                user = CustomUser.objects.get(id=user_id)  # Changed to CustomUser
            except Lead.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "Lead not found"
                }, status=404)
            except CustomUser.DoesNotExist:  # Changed to CustomUser
                return JsonResponse({
                    "success": False,
                    "error": "User not found"
                }, status=404)

            # Update lead assignment
            lead.assigned_to = user
            lead.save()

            return JsonResponse({
                "success": True,
                "message": f"Lead successfully assigned to {user.username}"
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON data"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
    
    return JsonResponse({
        "success": False,
        "error": "Only POST method is allowed"
    }, status=405)

def editLead(request, lead_id):
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated
    try:
        lead = Lead.objects.get(id=lead_id, assigned_to=request.user)  # Get the lead assigned to the logged-in user
    except Lead.DoesNotExist:
        messages.error(request, "Lead does not exist or you do not have permission to edit it")
        return redirect('salesmanDashboard')  # Redirect to dashboard if lead does not exist

    if request.method == 'POST':
        # lead.name = request.POST.get('name', lead.name)
        # lead.email = request.POST.get('email', lead.email)
        # lead.phone = request.POST.get('phone', lead.phone)
        # lead.city = request.POST.get('city', lead.city)
        # lead.company = request.POST.get('company', lead.company)
        # lead.role = request.POST.get('role', lead.role)
        lead.interest = request.POST.get('interest', lead.interest)
        lead.budget = request.POST.get('budget', lead.budget)
        lead.lead_source = request.POST.get('lead_source', lead.lead_source)
        lead.status = request.POST.get('status', lead.status)
        lead.priority = request.POST.get('priority', lead.priority)
        lead.notes = request.POST.get('notes', lead.notes)
        lead.save()  # Save the updated lead

        messages.success(request, "Lead updated successfully")
        return redirect('salesmanDashboard')  # Redirect to dashboard after editing

    context = {'lead': lead}  # Pass the lead to the template
    return render(request, 'salesmanPortal/editLead.html', context)  # Render the edit lead template

def logoutUser(request):
    if request.method == 'POST':
        logout(request)  # Log out the user
        messages.success(request, "You have been logged out successfully")
        return redirect('loginSalesman')  # Redirect to login page after logout
    
    return render(request, 'salesmanPortal/confirm_logout.html')  # Render the logout confirmation template

def viewLead(request, lead_id):
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated
    try:
        lead = Lead.objects.get(id=lead_id)  # Get the lead assigned to the logged-in user
    except Lead.DoesNotExist:
        messages.error(request, "Lead does not exist or you do not have permission to view it")
        return redirect('adminDashboard/')  # Redirect to dashboard if lead does not exist
    context = {'lead': lead}  # Pass the lead to

    return render(request, 'salesmanPortal/viewLead.html', context)  # Render the view lead template

@csrf_exempt
def deleteLead(request, lead_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method != 'DELETE':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        lead = Lead.objects.get(id=lead_id)
        lead.delete()
        return JsonResponse({'message': 'Lead deleted successfully'}, status=200)
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead does not exist'}, status=404)

def viewCategory(request):
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated

    categories = category.objects.all()
    # Exclude users where is_superuser is True
    salesman = CustomUser.objects.filter(is_superuser=False) # Filter out superusers
    context = {'categories': categories,
               'salesman' : salesman}  # Pass the categories to the template
    return render(request, 'salesmanPortal/viewCategory.html', context)  # Render the view category template

def addCategory(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginAdmin')  # Redirect to login if user is not authenticated or not an admin

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')

        if name:
            try:
                new_category = category.objects.create(name=name, description=description)
                messages.success(request, f"Category '{new_category.name}' added successfully")
                return redirect('viewCategory')  # Redirect to view categories after adding a new one
            except Exception as e:
                messages.error(request, f"Error adding category: {e}")
        else:
            messages.error(request, "Category name is required")

    return render(request, 'salesmanPortal/addCategory.html')  # Render the add category template  

def logOutAdmin(request):
    if request.method == 'POST':
        logout(request)  # Log out the user
        messages.success(request, "You have been logged out successfully")
        response = redirect('loginAdmin')  # Redirect to login page after logout
        # Invalidate browser history by setting headers
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    return render(request, 'salesmanPortal/confirm_logout_admin.html')  # Render the logout confirmation template for admin

def viewSalesman(request, email):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginAdmin')  # Redirect to login if user is not authenticated or not an admin

    try:
        salesman = CustomUser.objects.get(email=email, is_superuser=False)  # Get the salesman by email
    except CustomUser.DoesNotExist:
        messages.error(request, "Salesman does not exist")
        return redirect('viewCategory')  # Redirect if salesman not found

    # Get the leads assigned to this salesman
    assigned_leads = Lead.objects.filter(assigned_to=salesman)
    assigned_leads_count = assigned_leads.count()

    context = {
        'selected_salesman': salesman,
        'assigned_leads_count': assigned_leads_count,
        'assigned_leads': assigned_leads,  # Pass the leads to the template
    }
    return render(request, 'salesmanPortal/viewSalesman.html', context)  # Render the view salesman template
