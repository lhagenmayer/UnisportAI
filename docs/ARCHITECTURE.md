# UnisportAI Application Architecture Documentation

## Table of Contents
1. [State Management Flow](#state-management-flow)
2. [Navigation Flow](#navigation-flow)
3. [Filter System](#filter-system)
4. [Data Flow](#data-flow)
5. [Page Specifications](#page-specifications)

---

## State Management Flow

All state management is centralized in `data/state_manager.py` to ensure consistency and maintainability.

### State Categories

#### 1. Filter State
Managed through `get_filter_state()` and `set_filter_state()`:
- **`intensity`**: List of selected intensity levels (e.g., ['low', 'medium', 'high'])
- **`focus`**: List of selected focus areas (e.g., ['cardio', 'strength'])
- **`setting`**: List of selected settings (e.g., ['indoor', 'outdoor'])
- **`location`**: List of selected locations
- **`weekday`**: List of selected weekdays (e.g., ['Monday', 'Tuesday'])
- **`offers`**: List of selected sport activities (by name)
- **`search_text`**: Text search query
- **`show_upcoming_only`**: Boolean for showing only upcoming events
- **`hide_cancelled`**: Boolean for hiding cancelled courses
- **`date_start`**: Start date filter
- **`date_end`**: End date filter
- **`time_start`**: Start time filter
- **`time_end`**: End time filter

#### 2. Navigation State
Managed through dedicated functions:
- **`state_selected_offer`**: Currently selected sport offer (Dict)
  - Access: `get_selected_offer()`, `set_selected_offer()`, `clear_selected_offer()`
- **`state_nav_offer_hrefs`**: Navigation offer hrefs (List[str])
  - Access: `get_nav_offer_hrefs()`, `set_nav_offer_hrefs()`, `clear_nav_offer_hrefs()`
- **`state_page2_multiple_offers`**: Multiple offers selection (List[str])
  - Access: `get_multiple_offers()`, `set_multiple_offers()`, `has_multiple_offers()`
- **`state_selected_offers_multiselect`**: Multiselect state for offers
  - Access: `get_selected_offers_multiselect()`, `clear_selected_offers_multiselect()`
- **`state_nav_date`**: Navigation date (str)
  - Access: `get_nav_date()`, `set_nav_date()`, `clear_nav_date()`

#### 3. Data State
- **`state_sports_data`**: Cached sports offers data
  - Access: `get_sports_data()`, `set_sports_data()`

#### 4. User State
- **`user_id`**: Current user's database ID
  - Access: `get_user_id()`, `set_user_id()`, `clear_user_id()`
- **`user_activities`**: List of user activity logs
  - Access: `get_user_activities()`, `add_user_activity()`, `clear_user_activities()`

### User Preferences Loading

**Function**: `_ensure_preferences_loaded()`

**Trigger**: Called automatically on first `get_filter_state()` call

**Flow**:
1. Check if preferences already loaded (`_prefs_loaded` flag)
2. Get user's `sub` from authentication
3. Load user profile from database via `get_user_from_db()`
4. Map database columns to filter state keys:
   - `preferred_intensities` → `intensity`
   - `preferred_focus` → `focus`
   - `preferred_settings` → `setting`
   - `favorite_location_names` → `location`
   - `preferred_weekdays` → `weekday` (converts DB codes to UI strings)
5. Load favorite sports by converting hrefs to names
6. Set `_prefs_loaded` flag to prevent reloading

**Error Handling**: Silent failure with logging - defaults to empty values if preferences can't be loaded

---

## Navigation Flow

### Page Structure

```
streamlit_app.py (Entry Point)
├── Authentication Check
├── User Menu Rendering
└── Navigation Setup
    ├── pages/overview.py (Home)
    ├── pages/details.py (Course Dates)
    ├── pages/athletes.py (Sportfreunde)
    └── pages/profile.py (My Profile)
```

### Navigation Paths

#### 1. Overview → Details
**Trigger**: User clicks "Details anzeigen" button on a sport card

**State Changes**:
```python
set_selected_offer(offer)  # Store selected offer
st.switch_page("pages/details.py")
```

**Details Page Behavior**:
- Loads events for the selected offer
- Displays offer details (intensity, focus, setting, rating)
- Shows description if available
- Renders event list with "Going" buttons

#### 2. Overview → Details (Multiple Offers)
**Use Case**: When multiple levels of same sport exist (e.g., "Yoga Level 1", "Yoga Level 2")

**State Changes**:
```python
set_nav_offer_hrefs([href1, href2, ...])  # Store all related offer hrefs
set_multiple_offers([href1, href2, ...])
set_selected_offer(first_offer)
st.switch_page("pages/details.py")
```

**Details Page Behavior**:
- Detects multiple offers via `has_multiple_offers()`
- Shows multiselect filter in sidebar
- Combines events from all selected offers
- Removes duplicates by kursnr + time

#### 3. Overview → Athletes
**Trigger**: User navigates via top navigation

**Purpose**: Find and connect with other users (friends system)

#### 4. Overview → Profile
**Trigger**: User navigates via top navigation

**Purpose**: Manage user profile, preferences, and settings

### State Cleanup on Navigation

When navigating to Details page, the following cleanup occurs:
```python
if get_nav_offer_hrefs():
    # Store multiple offers
    set_multiple_offers(nav_offer_hrefs)
    
    # Clean up navigation state
    clear_nav_offer_hrefs()
    clear_nav_offer_name()
    clear_selected_offers_multiselect()
```

---

## Filter System

### Filter Architecture

Filters are rendered in the shared sidebar (`data/shared_sidebar.py`) and organized using Streamlit expanders.

### Filter Categories

#### 1. Quick Search (Always Visible)
- **Component**: `st.text_input`
- **State Key**: `search_text`
- **Applies To**: Overview page - filters sport names
- **Position**: Top of sidebar

#### 2. Activity Type Filters (Main Page)
**Expander**: "🎯 Activity Type" (expanded by default)

**Filters**:
- **Intensity**: Multiselect of intensity levels
  - State: `intensity`
  - Options: Extracted from sports data
  
- **Focus**: Multiselect of focus areas
  - State: `focus`
  - Options: Extracted from sports data
  
- **Setting**: Multiselect of settings
  - State: `setting`
  - Options: Extracted from sports data
  
- **Show Upcoming Only**: Checkbox
  - State: `show_upcoming_only`
  - Default: `True`

#### 3. Course Filters (Detail Page)
**Condition**: Only shown when `filter_type='detail'` and events data exists

##### a. Selected Activities (Multiple Offers Only)
**Expander**: "🎯 Selected Activities" (expanded)
**Condition**: `has_multiple_offers() == True`

- **Component**: Multiselect of sport activities
- **State**: `state_selected_offers_multiselect`
- **Options**: Offer hrefs formatted with offer names
- **Shows**: Count of selected activities

##### b. Sport & Status
**Expander**: "🏃 Sport & Status" (expanded)
**Condition**: `has_multiple_offers() == False`

**Filters**:
- **Sport**: Multiselect of sport names
  - State: `offers`
  - Options: Extracted from events data
  - Pre-selected: Current selected offer (if any)
  
- **Hide Cancelled**: Checkbox
  - State: `hide_cancelled`
  - Default: `True`

##### c. Date & Time
**Expander**: "📅 Date & Time" (collapsed by default)

**Filters**:
- **Date Range**:
  - From: `date_start` (st.date_input)
  - To: `date_end` (st.date_input)
  - Pre-selected: Navigation date if available
  
- **Time Range**:
  - From: `time_start` (st.time_input)
  - To: `time_end` (st.time_input)
  - Special handling: 00:00 is treated as "no filter"

##### d. Location & Day
**Expander**: "📍 Location & Day" (collapsed by default)

**Filters**:
- **Location**: Multiselect
  - State: `location`
  - Options: Extracted from events data
  
- **Weekday**: Multiselect
  - State: `weekday`
  - Options: Monday-Sunday (displayed in German)
  - Stored as English weekday names internally

### Filter Actions

#### Save Filters
**Button**: "💾 Save"
**Action**: Saves current filter values to user preferences in database

**Saved Values**:
- `intensity` → `preferred_intensities`
- `focus` → `preferred_focus`
- `setting` → `preferred_settings`
- `location` → `favorite_location_names`
- `weekday` → `preferred_weekdays` (converted to DB codes)

**Function**: `save_sidebar_preferences()` in `data/user_management.py`

#### Navigate Home
**Button**: "🏠 Home" (Detail page only)
**Action**: `st.switch_page("pages/overview.py")`

---

## Data Flow

### Overview Page Data Flow

```
1. Load Data
   ├── get_offers_with_stats() → Sports offers with metadata
   ├── count_upcoming_events_per_offer() → Event counts per offer
   └── get_trainers_for_all_offers() → Trainer info per offer

2. Store in State
   └── set_sports_data(offers) → Cache for sidebar

3. Render Sidebar
   └── render_shared_sidebar(filter_type='main', sports_data=offers)

4. Apply Filters
   ├── get_filter_state() for each filter
   ├── filter_offers() → Base filtering (intensity, focus, setting, search)
   └── filter_offers_by_events() → Detail filtering if detail filters active
       └── get_events_by_offer_mapping() → Optimized event loading

5. Display Results
   └── For each filtered offer:
       ├── Display card with info
       ├── Show upcoming dates (expandable)
       └── "Details" button → Navigate to details page
```

### Details Page Data Flow

```
1. Check Navigation State
   ├── get_nav_offer_hrefs() → Check if coming from multi-offer navigation
   └── If yes:
       ├── set_multiple_offers()
       ├── set_selected_offer()
       └── Clear navigation state

2. Determine Display Mode
   ├── has_selected_offer() → Single offer mode
   ├── has_multiple_offers() → Multiple offer mode
   └── Neither → All events mode

3. Load Events
   ├── Single offer: get_events_for_offer(href)
   ├── Multiple offers:
   │   ├── get_all_events()
   │   ├── Filter by selected offer hrefs
   │   └── Remove duplicates
   └── All: get_all_events()

4. Render Sidebar
   └── render_shared_sidebar(filter_type='detail', events=events)

5. Apply Filters
   ├── get_filter_state() for each filter
   └── Manual filtering:
       ├── Sport name filter
       ├── Cancelled filter
       ├── Date range filter
       ├── Location filter
       ├── Weekday filter
       └── Time range filter

6. Display Events
   └── For each filtered event:
       ├── Format date/time
       ├── Check user "going" status
       ├── Get friends going
       ├── Display event card
       └── "Going" / "Cancel" button
           └── mark_event_going() / unmark_event_going()
               ├── Update friend_course_notifications table
               └── Notify friends
```

### Athletes Page Data Flow

```
1. Load Data
   ├── get_user_id() → Current user
   └── get_public_users() → All public profiles

2. Display Tabs
   ├── Tab 1: All Athletes
   │   ├── Display public users
   │   ├── get_friend_status() for each
   │   └── Action buttons (send request, unfollow, etc.)
   │
   ├── Tab 2: Friend Requests
   │   ├── get_pending_requests()
   │   └── Accept/Reject buttons
   │
   └── Tab 3: My Friends
       └── get_user_friends()

3. Friend Actions
   ├── send_friend_request() → Create friend_requests record
   ├── accept_friend_request() → Create user_friends records (bidirectional)
   ├── reject_friend_request() → Update friend_requests status
   └── unfollow_user() → Delete user_friends records (both directions)
```

### Profile Page Data Flow

```
1. Load User Profile
   └── get_user_profile() → Complete user data from DB

2. Display Tabs
   ├── Tab 1: Information
   │   ├── Display user info
   │   ├── Show TOS/Privacy acceptance status
   │   └── Edit bio
   │
   ├── Tab 2: Preferences
   │   ├── Load current favorites: get_user_favorites()
   │   ├── Edit favorites, notifications, theme
   │   └── Save: update_user_favorites() + update_user_preferences()
   │
   ├── Tab 3: Calendar
   │   └── Show registered courses count
   │
   ├── Tab 4: Visibility
   │   ├── Public profile toggle
   │   └── Friend count display
   │
   └── Tab 5: Activity
       └── Display user_activities from state

3. Data Updates
   ├── Bio: Update users.bio
   ├── Preferences: Update users.preferences (JSON)
   ├── Favorites: Update user_favorites table
   └── Visibility: Update users.is_public
```

---

## Page Specifications

### streamlit_app.py (Entry Point)

**Purpose**: Authentication gate and navigation setup

**Flow**:
1. Check authentication: `is_logged_in()`
2. If not logged in: `show_login_page()` and stop
3. Check token expiry: `check_token_expiry()`
4. Sync user to Supabase: `sync_user_to_supabase()`
5. Render user menu: `render_user_menu()` (in sidebar)
6. Define pages and navigation
7. Run selected page

**State Access**: None (delegates to pages)

### pages/overview.py (Sports Overview)

**Purpose**: Browse and filter all sports activities

**Data Sources**:
- `get_offers_with_stats()`: Sports offers with ratings
- `count_upcoming_events_per_offer()`: Event counts
- `get_trainers_for_all_offers()`: Trainer info
- `get_events_for_offer()`: Events for date preview

**State Usage**:
- **Reads**: All filter states
- **Writes**: 
  - `state_sports_data` (via `set_sports_data()`)
  - `state_selected_offer` (via `set_selected_offer()`)

**Filters Applied**:
- Search text
- Show upcoming only
- Intensity, Focus, Setting
- Optional: Date, Time, Location, Weekday (if any are set)

**Navigation Targets**:
- Details page (single offer)
- Details page (multiple offers - if clicking "Show all dates")

### pages/details.py (Course Dates)

**Purpose**: View and register for specific course dates

**Data Sources**:
- `get_events_for_offer()`: Events for single offer
- `get_all_events()`: Events for multiple offers or all
- `get_user_id()`: Current user ID
- `is_user_going_to_event()`: Check user registration
- `get_friends_going_to_event()`: Friend registrations

**State Usage**:
- **Reads**: 
  - Navigation state (offer hrefs, nav date)
  - All filter states
  - Selected offer
- **Writes**:
  - Clears navigation state after processing
  - Updates multiple offers state

**Filters Applied**:
- Sport name (if not in multiple offers mode)
- Hide cancelled
- Date range
- Location
- Weekday
- Time range

**Actions**:
- **Going Button**: 
  - `mark_event_going()`
  - Creates friend_course_notifications records
  - Notifies friends
- **Cancel Button**: `unmark_event_going()`

**Navigation Targets**:
- Home (via sidebar button)

### pages/athletes.py (Sportfreunde)

**Purpose**: Social features - find and connect with other athletes

**Data Sources**:
- `get_public_users()`: All public profiles
- `get_friend_status()`: Check friendship status
- `get_pending_requests()`: Incoming friend requests
- `get_user_friends()`: Current friends

**State Usage**:
- **Reads**: None (except user authentication)
- **Writes**: None (all data in database)

**Tabs**:
1. **All Athletes**: Browse public profiles, send friend requests
2. **Requests**: Accept/reject incoming friend requests
3. **My Friends**: View friend list

**Actions**:
- `send_friend_request()`: Send request
- `accept_friend_request()`: Accept and create friendship
- `reject_friend_request()`: Reject request
- `unfollow_user()`: Remove friendship

### pages/profile.py (My Profile)

**Purpose**: Manage user profile, preferences, and settings

**Data Sources**:
- `get_user_profile()`: Complete user profile
- `get_user_favorites()`: Favorite sports
- `get_user_activities()`: Activity log from state

**State Usage**:
- **Reads**: 
  - `user_activities` (via `get_user_activities()`)
- **Writes**: None directly (updates go to database)

**Tabs**:
1. **Information**: View/edit basic info and bio
2. **Preferences**: Manage favorites, notifications, theme
3. **Calendar**: View registered courses
4. **Visibility**: Public profile toggle
5. **Activity**: View recent activity log

**Actions**:
- Update bio: `users.bio`
- Save preferences: `update_user_favorites()`, `update_user_preferences()`
- Update visibility: `users.is_public`

---

## Key Design Patterns

### 1. Centralized State Management
All state operations go through `state_manager.py` functions to ensure:
- Consistent state access
- Automatic preference loading
- Type safety
- Easy debugging

### 2. Lazy Loading
User preferences are loaded only once on first filter access:
- Reduces database queries
- Cached with `_prefs_loaded` flag
- Silent failure for robustness

### 3. Navigation State Cleanup
After processing navigation state, it's immediately cleaned up to prevent stale data:
- Prevents UI confusion
- Ensures fresh state on each navigation
- Explicit state lifecycle

### 4. Optimized Data Loading
Events are loaded efficiently:
- Single query per offer: `get_events_for_offer()`
- Bulk query for multiple: `get_all_events()` with filtering
- Cached sports data: `state_sports_data`
- Aggregated counts: `count_upcoming_events_per_offer()`

### 5. Filter Inheritance
Filters persist across page navigation:
- User selections are maintained in session state
- Preferences can be saved to database
- Default values from user preferences on first load

---

## Error Handling

### State Loading Errors
- **Behavior**: Silent failure with logging
- **Fallback**: Empty default values
- **Reason**: Prevents app crashes, allows guest usage

### Database Errors
- **Display**: Error messages to user via `st.error()`
- **Logging**: Server-side logging for debugging
- **Recovery**: Graceful degradation (empty lists, default values)

### Navigation Errors
- **Missing State**: Assumes "all offers" or "all events" mode
- **Invalid Data**: Filters out invalid entries
- **Stale State**: Automatic cleanup on page entry

---

## Performance Considerations

### 1. Database Query Optimization
- Bulk queries over individual queries
- Cached sports data in session state
- Indexed database columns (href, kursnr, start_time)

### 2. State Management
- One-time preference loading with caching
- Lazy loading (load only when needed)
- Minimal state updates (only on user action)

### 3. UI Rendering
- Expanders to hide unused filters (collapsed by default)
- Pagination in future (currently showing all results)
- Event deduplication for multiple offers

### 4. Security
- Rate limiting via `rate_limit_check()`
- Input validation before database writes
- HTML sanitization via `sanitize_html()`

---

## Future Enhancements

### State Management
- [ ] Add state versioning for migration
- [ ] Implement state persistence across sessions
- [ ] Add state debugging panel for development

### Filters
- [ ] Save multiple filter presets
- [ ] Quick filter templates (e.g., "Evening classes", "Weekend yoga")
- [ ] Filter analytics (most used filters)

### Navigation
- [ ] Breadcrumb navigation
- [ ] Back button functionality
- [ ] Deep linking support

### Data Flow
- [ ] Real-time updates via Supabase subscriptions
- [ ] Pagination for large result sets
- [ ] Infinite scroll for events

---

*Last Updated: 2024*
*Version: 1.0*
