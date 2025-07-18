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

        # Check if user is approved before authenticating
        if not getattr(user, 'is_approved', False):
            messages.error(request, "Your account is not approved yet. Please contact the administrator.")
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
    leads_queryset = Lead.objects.filter(category_id=category_id)  # Filter by category first
    selected_category = category.objects.filter(id=category_id).first() if category_id else None
    created_on_date_str = request.GET.get('created_on_date')

    # Apply single-day date filter if present
    if created_on_date_str:
        try:
            selected_date = datetime.strptime(created_on_date_str, '%Y-%m-%d').date()
            # Filter leads created specifically on this date (compare only the date part)
            leads_queryset = leads_queryset.filter(created_at__date=selected_date)
        except ValueError:
            created_on_date_str = None  # Reset to not pre-fill if invalid

    leads = leads_queryset.order_by('-updated_at')

    total_leads = leads.count()
    new_leads = leads.filter(status='New').count()
    contacted_leads = leads.filter(status='Contacted').count()
    qualified_leads = leads.filter(status='Converted').count()  # Or 'Won' based on your model/logic

    converted_leads = qualified_leads  # Using 'Qualified' as a proxy for converted, adjust as needed

    salesmen = CustomUser.objects.filter(is_staff=False)  # Assuming non-staff are salesmen
    total_salesmen = salesmen.count()

    context = {
        'selected_category': selected_category,  # Pass the category name for the header
        'category_id': category_id,
        'total_leads': total_leads,
        'total_salesmen': total_salesmen,
        'new_leads': new_leads,
        'contacted_leads': contacted_leads,
        'converted_leads': converted_leads,
        'leads': leads,
        'users': salesmen,  # Pass salesmen (non-staff users) for assignment dropdown
        'current_created_on_date': created_on_date_str,  # Pass back to template for pre-filling
    }
    return render(request, 'salesmanPortal/adminDashboard.html', context)


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
    salesman = CustomUser.objects.filter(is_superuser=False,is_approved = True) # Filter out superusers
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

def todayLeads(request):
    if not request.user.is_authenticated:
        return redirect('loginSalesman')  # Redirect to login if user is not authenticated
    today = localdate()  # Get the current date (timezone-aware)
    # Filter leads where updated_at's date matches today
    today_leads = Lead.objects.filter(updated_at__date=today)
    context = {
        'today_leads': today_leads,  # Pass the leads updated today to the template
    }
    return render(request, 'salesmanPortal/todayLeads.html', context)  # Render the today leads template

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
