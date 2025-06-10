from django.shortcuts import render,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from .models import Lead, category  # Ensure Lead and category models are imported
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import json
def loginSalesman(request):
    page = 'login'
    if(request.method == 'POST'):
        username = request.POST.get('username')
        password = request.POST.get('password')
        try: 
            user = User.objects.get(username=username)  # Get the user by username
        except User.DoesNotExist:
            messages.error(request, "User does not exist")
        user = authenticate(request,username=username,password=password) # this will authenticate the user
        if user is not None:
            login(request,user) # this will log in the user and add in the session database
            return redirect('salesmanDashboard')  # Redirect to home page after login
        else:
            messages.error(request, "Username or password does not exist")
    context = {
        'page': page,
    }   
    return render(request, 'salesmanPortal/loginSalesmen.html',context)

def registerUser(request):
    form = UserCreationForm()
    context = {'form': form}
    if(request.method == 'POST'):
        form = UserCreationForm(request.POST)
        if(form.is_valid()):
            user = form.save(commit=False)
            user.save()  # Save the new user
            username = form.cleaned_data.get('username')  # Get the username from the form
            password = form.cleaned_data.get('password1')  # Get the password from the form
            user = authenticate(username=username, password=password)  # Authenticate the user
            login(request, user)  # Log in the user
            return redirect('salesmanDashboard')  # Redirect to home page after registration
        else:
            messages.error(request, "An error occurred during registration")
    return render(request, 'salesmanPortal/loginSalesmen.html',context)

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
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('viewCategory')  # Redirect to admin dashboard after login
        else:
            messages.error(request, "Invalid admin credentials")
    return render(request, 'salesmanPortal/loginAdmin.html')  # Render the admin login template

from django.db.models import F

def adminDashboard(request,category_id=None):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginAdmin')

    # Only leads that were actually updated after creation
    leads = Lead.objects.exclude(updated_at=F('created_at')).order_by('-updated_at')
    if category_id:
        leads = leads.filter(category_id=category_id)
    else:
        leads = leads.filter(category__isnull=False)
    total_leads = leads.count()  # Count only the filtered leads
    total_salesmen = User.objects.filter(is_staff=False).count()
    users = User.objects.all()
    if category_id:
        new_leads = Lead.objects.filter(status='New', category_id=category_id).count()  # Count 'New' leads for selected category
    else:
        new_leads = Lead.objects.filter(status='New').count()  # Count all 'New' leads
    contacted_leads = Lead.objects.filter(status='Contacted',category_id=category_id).count()  # Count leads with status 'Contacted'
    in_discussion_leads = Lead.objects.filter(status='In Discussion',category_id=category_id).count()  # Count leads with status 'In Discussion'
    not_interested_leads = Lead.objects.filter(status='Not Interested',category_id=category_id).count()  # Count leads with status 'Not Interested'
    converted_leads = Lead.objects.filter(status='Converted',category_id=category_id).count()  # Count leads with status 'Converted'
    #fetch the name of the category
    selected_category = None
    if category_id:
        selected_category = category.objects.filter(id=category_id).first()
    context = {
        'total_leads': total_leads,
        'total_salesmen': total_salesmen,
        'leads': leads,
        'users': users,
        'new_leads': new_leads,
        'contacted_leads': contacted_leads,
        'in_discussion_leads': in_discussion_leads,
        'not_interested_leads': not_interested_leads,
        'converted_leads': converted_leads,
        'selected_category': selected_category,
        'category_id': category_id,  # Pass the category ID to the template
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



@csrf_exempt  # OR use @require_POST with CSRF token if you prefer security
def assign_lead_ajax(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lead_id = data.get("lead_id")
            user_id = data.get("user_id")

            lead = Lead.objects.get(id=lead_id)
            user = User.objects.get(id=user_id)

            lead.assigned_to = user
            lead.save()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid method"})

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
    categories = category.objects.all() # Get distinct categories from leads
    context = {'categories': categories}  # Pass the categories to the template
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
