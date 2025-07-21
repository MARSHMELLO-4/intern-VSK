from venv import logger
from django.shortcuts import get_object_or_404, render,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse, HttpResponseBadRequest
from .models import Lead, category ,CustomUser # Ensure Lead and category models are imported
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User 
import json
from .forms import CustomUserCreationForm
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import F, Count
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
import csv
from datetime import date, datetime,time 


def loginSalesman(request):
    # If already logged in, redirect to dashboard
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('salesmanDashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        try:
            user = CustomUser.objects.get(email=email)
            if not user.is_approved:
                messages.error(request, "Account not approved")
                return redirect('loginSalesman')
            
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                if remember_me:
                    request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
                else:
                    request.session.set_expiry(0)
                return redirect('salesmanDashboard')
            else:
                messages.error(request, "Invalid credentials")
        except CustomUser.DoesNotExist:
            messages.error(request, "User does not exist")
    
    return render(request, 'salesmanPortal/loginSalesmen.html', {'page': 'login'})

from .forms import CustomUserCreationForm

def registerUser(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = False  # Mark user as not approved
            user.save()
            messages.success(request, 'Registration successful! Please wait for admin approval before logging in.')
            return redirect('loginSalesman')  # Redirect to login page after registration
        else:
            print(form.errors)
            messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'salesmanPortal/salesmanRegister.html', {'form': form})  # Render the registration template with the form

def salesmanDashboard(request):
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated

    # Leads assigned to the logged-in user
    assigned_leads = Lead.objects.filter(assigned_to=request.user)
    total_leads = assigned_leads.count()

    # Contacted leads assigned to the user
    contacted_leads = assigned_leads.filter(status='Contacted').count()

    # Leads that are assigned to the user but not contacted
    not_contacted_leads = assigned_leads.exclude(status='Contacted').count()

    context = {
        'leads': assigned_leads,
        'total_leads': total_leads,
        'contacted_leads': contacted_leads,
        'not_contacted_leads': not_contacted_leads,
    }
    return render(request, 'salesmanPortal/salesmanDashboard.html', context)

def loginAdmin(request):
    # If already logged in, redirect to dashboard
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('viewCategory')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            else:
                request.session.set_expiry(0)
            return redirect('viewCategory')
        else:
            messages.error(request, "Invalid credentials")
    
    return render(request, 'salesmanPortal/loginAdmin.html')



def adminDashboard(request, category_id=None):
    # Fetch all categories for the sidebar (if you still have a sidebar)
    try:
        categories = category.objects.all()
    except:
        categories = [] # Fallback if category model is not used or handled differently

    selected_category = None
    leads = Lead.objects.all()

    # Filter leads by category from URL if category_id is provided
    if category_id:
        selected_category_obj = get_object_or_404(category, id=category_id)
        leads = leads.filter(category=selected_category_obj)
        selected_category = selected_category_obj.name
    
    # Date filter
    current_created_on_date = request.GET.get('created_on_date')
    if current_created_on_date:
        try:
            date_obj = datetime.strptime(current_created_on_date, '%Y-%m-%d').date()
            leads = leads.filter(created_at__date=date_obj)
        except ValueError:
            pass # Invalid date format, ignore filter

    # NEW: Status Filter
    status_filter = request.GET.get('status')
    if status_filter:
        leads = leads.filter(status=status_filter)

    # NEW: Priority Filter
    priority_filter = request.GET.get('priority')
    if priority_filter:
        leads = leads.filter(priority=priority_filter)

    # Lead Filters (Assigned, Pending, All) - these should apply AFTER date, status, priority
    lead_filter = request.GET.get('lead_filter')
    if lead_filter == 'assigned':
        leads = leads.filter(assigned_to__isnull=False)
    elif lead_filter == 'pending':
        leads = leads.filter(assigned_to__isnull=True)
    # 'all' filter is default, no additional filtering needed here

    # Calculate stats based on the currently filtered leads
    total_leads = leads.count()
    new_leads = leads.filter(status='New').count()
    contacted_leads = leads.filter(status='Contacted').count()
    converted_leads = leads.filter(status='Converted').count()

    # Get all assignable users (salesmen)
    users = CustomUser.objects.filter(is_approved=True) # Adjust this filter as per your user roles

    # Total salesmen stat
    total_salesmen = users.count()

    # Get choices for dropdowns directly from the Lead model
    status_choices = Lead.STATUS_CHOICES
    priority_choices = Lead.PRIORITY_CHOICES

    context = {
        'category_id': category_id, # Pass category_id for URLs
        'selected_category': selected_category,
        'leads': leads.order_by('-created_at'), # Order for consistent display
        'total_leads': total_leads,
        'total_salesmen': total_salesmen,
        'new_leads': new_leads,
        'contacted_leads': contacted_leads,
        'converted_leads': converted_leads,
        'current_created_on_date': current_created_on_date, # Pass this back to pre-fill the date input
        'status_choices': status_choices,   # NEW: Pass status choices
        'priority_choices': priority_choices, # NEW: Pass priority choices
        'users': users, # Pass users for assignment dropdowns
    }
    return render(request, 'salesmanPortal/adminDashboard.html', context) # Replace 'your_template_name.html' with your actual template path


import pandas as pd
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import localdate
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



@csrf_exempt # Use this for simplicity in development, but for production, use proper CSRF protection
@csrf_exempt
def assign_lead_ajax(request):
    print(f"\n--- assign_lead_ajax hit! Method: {request.method} --- Current Time: {datetime.now()}")
    if request.method == 'POST':
        try:
            print("Processing POST request for single lead assignment.")
            data = json.loads(request.body)
            lead_id = data.get('lead_id')
            user_id = data.get('user_id') # This can be null for unassign

            print(f"Received lead_id: {lead_id}, user_id: {user_id}")

            if not lead_id:
                print("Error: lead_id is missing or invalid.")
                return JsonResponse({'success': False, 'error': 'Lead ID is required.'}, status=400) # Bad Request

            try:
                lead = Lead.objects.get(id=lead_id)
                print(f"Found lead: {lead.name} (ID: {lead.id})")
            except Lead.DoesNotExist:
                print(f"Lead with ID {lead_id} not found. Returning 404.")
                return JsonResponse({'success': False, 'error': 'Lead not found.'}, status=404) # Not Found

            if user_id:
                try:
                    user = CustomUser.objects.get(id=user_id)
                    lead.assigned_to = user
                    message = f"Lead assigned to {user.get_full_name() or user.username} successfully."
                    print(f"Assigned lead {lead.id} to user {user.id}.")
                except CustomUser.DoesNotExist:
                    print(f"Salesman with ID {user_id} not found. Returning 404.")
                    return JsonResponse({'success': False, 'error': 'Salesman not found.'}, status=404) # Not Found
            else:
                lead.assigned_to = None # Unassign
                message = "Lead unassigned successfully."
                print(f"Lead {lead.id} unassigned.")
            
            lead.save()
            print("Lead assignment saved. Returning success JSON.")
            return JsonResponse({'success': True, 'message': message}, status=200) # OK

        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: Request body is not valid JSON. Error: {e}")
            print(f"Raw request body: {request.body.decode('utf-8')}") # Print raw body to see what client sent
            return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400) # Bad Request
        except Exception as e:
            print(f"Unhandled exception in assign_lead_ajax: {e}")
            import traceback
            traceback.print_exc() # Print full traceback to console
            return JsonResponse({'success': False, 'error': f'An unexpected server error occurred: {str(e)}'}, status=500) # Internal Server Error
    else:
        print(f"Invalid request method: {request.method}. Expected POST.")
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405) # Method Not Allowed

@csrf_exempt
def bulk_assign_leads_ajax(request):
    print(f"\n--- bulk_assign_leads_ajax hit! Method: {request.method} --- Current Time: {datetime.now()}")
    if request.method == 'POST':
        try:
            print("Processing POST request for bulk lead assignment.")
            data = json.loads(request.body)
            lead_ids = data.get('lead_ids', [])
            user_id = data.get('user_id')

            print(f"Received lead_ids: {lead_ids}, user_id: {user_id}")

            if not lead_ids:
                print("Error: No leads selected for bulk assignment.")
                return JsonResponse({'success': False, 'error': 'No leads selected.'}, status=400) # Bad Request

            if not user_id:
                print("Error: No salesman selected for bulk assignment.")
                return JsonResponse({'success': False, 'error': 'No salesman selected.'}, status=400) # Bad Request
            
            try:
                user = CustomUser.objects.get(id=user_id)
                print(f"Assigning leads to user: {user.email} (ID: {user.id})")
            except CustomUser.DoesNotExist:
                print(f"Salesman with ID {user_id} not found. Returning 404.")
                return JsonResponse({'success': False, 'error': 'Salesman not found.'}, status=404) # Not Found
            
            # Update all selected leads
            updated_count = Lead.objects.filter(id__in=lead_ids).update(assigned_to=user)
            
            print(f"Successfully updated {updated_count} leads. Returning success JSON.")
            return JsonResponse({'success': True, 'message': f'{updated_count} lead(s) assigned successfully.'}, status=200) # OK
        
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: Request body is not valid JSON. Error: {e}")
            print(f"Raw request body: {request.body.decode('utf-8')}") # Print raw body to see what client sent
            return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400) # Bad Request
        except Exception as e:
            print(f"Unhandled exception in bulk_assign_leads_ajax: {e}")
            import traceback
            traceback.print_exc() # Print full traceback to console
            return JsonResponse({'success': False, 'error': f'An unexpected server error occurred: {str(e)}'}, status=500) # Internal Server Error
    else:
        print(f"Invalid request method: {request.method}. Expected POST.")
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405) # Method Not Allowed

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

@never_cache
@require_http_methods(["GET", "POST"])
def logoutUser(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out successfully")
        response = redirect('loginSalesman')
        # Clear session cookie and prevent caching
        response.delete_cookie('sessionid')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
        return response
    
    # GET request - show confirmation page
    return render(request, 'salesmanPortal/confirm_logout.html')

def viewLead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Get all users who are approved and not staff (assuming they are your salesmen)
    salesmen = CustomUser.objects.filter(is_approved=True, is_staff=False)

    context = {
        'lead': lead,
        'salesmen': salesmen, # Pass salesmen to the template
        'csrf_token': request.META.get('CSRF_COOKIE', ''), # Ensure CSRF token is available
    }
    return render(request, 'salesmanPortal/viewLead.html', context) # Make sure your template name is correct

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
    # Fetch all categories for the sidebar
    categories = Category.objects.all().order_by('name')

    # Fetch all salesmen for the 'Assigned To' filter
    # Assuming 'Salesman' is a custom user model or a profile related to User
    # Adjust this query if your salesmen are stored differently
    salesmen = User.objects.filter(is_salesman=True) # Example: filter by a flag

    # Start with all leads
    leads = Lead.objects.all()

    # Apply search query 'q' (name, email, company)
    search_query = request.GET.get('q')
    if search_query:
        leads = leads.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company__icontains=search_query)
        )

    # Apply status filter
    status_filter = request.GET.get('status')
    if status_filter:
        leads = leads.filter(status=status_filter)

    # Apply priority filter
    priority_filter = request.GET.get('priority')
    if priority_filter:
        leads = leads.filter(priority=priority_filter)

    # Apply assigned_to filter
    assigned_to_filter = request.GET.get('assigned_to')
    if assigned_to_filter:
        leads = leads.filter(assigned_to__id=assigned_to_filter)

    # Apply category filter
    category_filter = request.GET.get('category')
    if category_filter:
        leads = leads.filter(category__id=category_filter)

    # --- NEW: Apply date filters ---
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str:
        try:
            # Convert string to date object
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            leads = leads.filter(date_created__gte=start_date) # __gte means "greater than or equal to"
        except ValueError:
            # Handle invalid date format if necessary, e.g., log it or show an error message
            pass # For now, just ignore bad date format

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            # For end date, filter by less than or equal to the end of that day.
            # If your `date_created` is a DateTimeField, you might want to adjust
            # to include the whole day, e.g., `date_created__lte=end_date + timedelta(days=1)`
            # or `date_created__date__lte=end_date` if using a DateField lookup.
            # Assuming `date_created` is a DateField or you want to match the date part:
            leads = leads.filter(date_created__lte=end_date)
        except ValueError:
            pass # For now, just ignore bad date format
    # --- END NEW DATE FILTERS ---


    # Ensure leads are ordered (e.g., by creation date or name)
    leads = leads.order_by('-date_created') # Or whatever default ordering you prefer

    # Prepare choices for status and priority dropdowns (assuming these are defined in your Lead model)
    status_choices = Lead.STATUS_CHOICES # Assuming this is a tuple of tuples in Lead model
    priority_choices = Lead.PRIORITY_CHOICES # Assuming this is a tuple of tuples in Lead model

    context = {
        'categories': categories,
        'leads': leads,
        'salesmen': salesmen,
        'status_choices': status_choices,
        'priority_choices': priority_choices,
        # 'request.GET' is automatically available in the template, but good practice to pass if you modify it.
    }
    return render(request, 'salesmanPortal/viewCategory.html', context) # Replace 'your_template_name.html'

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

@never_cache
@require_http_methods(["GET", "POST"])
def logOutAdmin(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out successfully")
        response = redirect('loginAdmin')
        # Clear session cookie and prevent caching
        response.delete_cookie('sessionid')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
        return response
    
    # GET request - show confirmation page
    return render(request, 'salesmanPortal/confirm_logout_admin.html')

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

def contactUs(request):
    return render(request, 'salesmanPortal/terms_contact.html')  # Render the contact us template

def requestPage(request):
    #get all the custom users with the is_approved field set to False
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated
    pending_users = CustomUser.objects.filter(is_superuser = False,is_approved=False)
    context = {
        'pending_users': pending_users,  # Pass the pending users to the template
    }
    return render(request, 'salesmanPortal/requestPage.html',context) 

def is_admin(user):
    return user.is_staff 
 # Render the request page template # type: ignore # Keep your access control
@csrf_exempt
def approve_users_view(request): # Handles batch approval
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            emails_to_approve = data.get('emails') # Expecting an array of emails

            if not emails_to_approve or not isinstance(emails_to_approve, list):
                logger.warning("Invalid or empty list of emails provided for approval.")
                return JsonResponse({'success': False, 'error': 'Invalid or empty list of emails provided.'}, status=400)

            approved_count = 0
            errors = []

            with transaction.atomic(): # Ensure all or none are approved for data integrity
                for email in emails_to_approve:
                    try:
                        # Find the user by email and ensure they are NOT already approved
                        user = CustomUser.objects.get(email=email, is_approved=False)
                        user.is_approved = True
                        # If you also use is_active for login control, set it here:
                        user.is_active = True # IMPORTANT: Set is_active to True so they can log in
                        user.save()
                        approved_count += 1
                    except CustomUser.DoesNotExist:
                        errors.append(f"User with email '{email}' not found or already approved.")
                        logger.info(f"User with email '{email}' not found or already approved for approval request.")
                    except Exception as e:
                        errors.append(f"Error approving user '{email}': {str(e)}")
                        logger.error(f"Error approving user {email}: {e}")
            
            if approved_count > 0:
                messages.success(request, f"{approved_count} user(s) approved successfully.")
            if errors:
                # Use messages for errors too, which will show on page reload/next request
                messages.error(request, "Some users could not be approved: " + "; ".join(errors))
                # For AJAX, you might also want to send back detailed errors in the JSON response
                # return JsonResponse({'success': False, 'approved_count': approved_count, 'errors': errors}, status=200)

            return JsonResponse({'success': True, 'approved_count': approved_count, 'errors': errors})

        except json.JSONDecodeError:
            logger.error("Invalid JSON in approve_users_view request body.")
            return JsonResponse({'success': False, 'error': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            logger.exception("Unexpected error in approve_users_view:") # Logs full traceback
            return JsonResponse({'success': False, 'error': 'Server error during approval process. Please check logs.'}, status=500)
    
    # If it's not a POST request to this endpoint
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

# def todayLeads(request):
#     if not request.user.is_authenticated:
#         return redirect('loginSalesman')  # Redirect to login if user is not authenticated
#     today = localdate()  # Get the current date (timezone-aware)
#     # Filter leads where updated_at's date matches today
#     today_leads = Lead.objects.filter(updated_at__date=today)
#     context = {
#         'today_leads': today_leads,  # Pass the leads updated today to the template
#     }
#     return render(request, 'salesmanPortal/todayLeads.html', context)  # Render the today leads template

def deleteSalesman(request, email):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('loginAdmin')  # Redirect to login if user is not authenticated or not an admin

    try:
        salesman = CustomUser.objects.get(email=email, is_superuser=False)  # Get the salesman by email
        salesman.delete()  # Delete the salesman
        messages.success(request, f"Salesman with email '{email}' deleted successfully")
    except CustomUser.DoesNotExist:
        messages.error(request, "Salesman does not exist")
    
    return redirect('viewCategory')  # Redirect to view categories after deletion

@csrf_exempt  # Use this decorator for simplicity with AJAX POST. Consider more secure methods for production.
def discard_users_view(request):
    """
    Handles POST requests to discard (deactivate and delete) user accounts.

    Expects a JSON body with a list of emails in the 'emails' key.
    Deactivates and deletes the CustomUser accounts corresponding to the provided emails.
    Returns a JSON response indicating success or an error.
    """
    if request.method == 'POST':
        try:
            # Load the JSON data from the request body
            data = json.loads(request.body)
            emails_to_discard = data.get('emails', [])

            # Validate that 'emails' is a list
            if not isinstance(emails_to_discard, list):
                return HttpResponseBadRequest(json.dumps({'success': False, 'error': 'Emails must be a list.'}), content_type="application/json")

            # If no emails are provided, return a success message indicating no action needed
            if not emails_to_discard:
                return JsonResponse({'success': True, 'message': 'No users specified for discard.'})

            discarded_count = 0
            # Filter users by email to find the ones to deactivate and delete
            users_to_update = CustomUser.objects.filter(email__in=emails_to_discard)

            # Iterate through the found users, deactivate and delete them
            for user in users_to_update:
                # Optional: Add checks here, e.g., to prevent discarding superusers
                # if not user.is_superuser:
                user.is_active = False  # Deactivate the user account
                user.save()  # Save the changes to the database
                user.delete()  # Delete the user from the table
                discarded_count += 1

            # Return a success JSON response with the count of discarded users
            return JsonResponse({
                'success': True,
                'message': f'{discarded_count} user(s) discarded and deleted successfully.'
            })

        except json.JSONDecodeError:
            # Handle cases where the request body is not valid JSON
            return HttpResponseBadRequest(json.dumps({'success': False, 'error': 'Invalid JSON in request body.'}), content_type="application/json")
        except Exception as e:
            # Catch any other unexpected errors and return a 500 server error response
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        # Handle cases where the request method is not POST (e.g., GET, PUT, DELETE)
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
from django.db.models import Count,Q
def viewBDAs(request):
    if not request.user.is_superuser:
        return redirect('salesmanDashboard')

    # ✅ Get the search query from the URL (?q=...)
    search_query = request.GET.get('q', None)

    # Start with the base queryset
    bda_queryset = CustomUser.objects.filter(
        is_superuser=False,
        is_approved=True
    )

    # ✅ If a search query exists, filter the queryset
    if search_query:
        bda_queryset = bda_queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Annotate and order the (potentially filtered) queryset
    bda_data = bda_queryset.order_by('first_name')

    context = {
        'bda_list': bda_data,
        'page_title': 'BDA Management',
        'search_query': search_query,  # ✅ Pass the query back to the template
    }
    
    return render(request, 'salesmanPortal/viewBDAs.html', context)

def downloadLeads(request):
    categories = category.objects.all().order_by('name')
    context = {
        'categories': categories,
        'category_id': 0, 
    }

    if request.method == 'POST':
        scope_option = request.POST.get('scope_option')
        filter_by_category = request.POST.get('filter_by_category') == 'on' 
        filter_by_date_range = request.POST.get('filter_by_date_range') == 'on'

        category_id = request.POST.get('category_id')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        leads_queryset = Lead.objects.all()

        if scope_option == 'assigned':
            leads_queryset = leads_queryset.filter(assigned_to__isnull=False)
        elif scope_option == 'pending':
            leads_queryset = leads_queryset.filter(assigned_to__isnull=True)

        if filter_by_category:
            if category_id:
                try:
                    category_obj = category.objects.get(id=category_id)
                    leads_queryset = leads_queryset.filter(category=category_obj)
                except category.DoesNotExist:
                    messages.error(request, "Selected category does not exist.")
                    return render(request, 'salesmanPortal/downloadLeads.html', context)
            else:
                messages.error(request, "Please select a category when filtering by category.")
                return render(request, 'salesmanPortal/downloadLeads.html', context)

        if filter_by_date_range:
            if start_date_str and end_date_str:
                try:
                    start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date() # Use imported datetime
                    end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()     # Use imported datetime
                    
                    end_datetime_inclusive = datetime.combine(end_date_obj, time.max) # Use imported datetime and time

                    leads_queryset = leads_queryset.filter(created_at__gte=start_date_obj, created_at__lte=end_datetime_inclusive)

                except ValueError:
                    messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
                    return render(request, 'salesmanPortal/downloadLeads.html', context)
            else:
                messages.error(request, "Please provide both start and end dates when filtering by date range.")
                return render(request, 'salesmanPortal/downloadLeads.html', context)
        
        leads_queryset = leads_queryset.order_by('created_at')

        if not leads_queryset.exists():
            messages.info(request, "No leads found for the selected criteria. Please adjust your filters.")
            return render(request, 'salesmanPortal/downloadLeads.html', context)

        response = HttpResponse(content_type='text/csv')
        # Use imported 'date' for today()
        response['Content-Disposition'] = f'attachment; filename="leads_data_{date.today().strftime("%Y%m%d")}.csv"' 

        writer = csv.writer(response)

        writer.writerow([
            'ID', 'Name', 'Email', 'Phone', 'Company', 'Role', 
            'Status', 'Priority', 'Category', 'Assigned To (Email)', 'Created At'
        ])

        for lead in leads_queryset:
            assigned_to_email = lead.assigned_to.email if lead.assigned_to else 'Unassigned'
            category_name = lead.category.name if lead.category else 'No Category'
            
            writer.writerow([
                lead.id,
                lead.name,
                lead.email or '', 
                lead.phone or '',
                lead.company or '',
                lead.role or '',
                lead.get_status_display(),
                lead.get_priority_display(),
                category_name,
                assigned_to_email,
                lead.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        return response

    return render(request, 'salesmanPortal/downloadLeads.html', context)