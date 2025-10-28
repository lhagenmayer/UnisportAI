// Edge Function to serve dynamic iCal feed for user's "going" events
// Accessible via: https://YOUR_PROJECT.supabase.co/functions/v1/ical-feed

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Get authorization token from query param
    // We use query param to avoid JWT verification issues
    const url = new URL(req.url)
    const token = url.searchParams.get('token')

    if (!token) {
      return new Response(JSON.stringify({ error: 'Missing token parameter. Add ?token=YOUR_TOKEN to the URL' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    // Create Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseKey)

    // NEW: Lookup user by ical_feed_token (personalized token)
    let userData = null
    
    // Try to find user by ical_feed_token
    console.log(`Looking up token: ${token}`)
    const { data: tokenUserData, error: userError } = await supabase
      .from('users')
      .select('id, email, name, sub, ical_feed_token')
      .eq('ical_feed_token', token)
      .single()

    console.log(`Token lookup result:`, userError, tokenUserData)

    if (!userError && tokenUserData) {
      // Found user by personalized token
      console.log(`Found user by token: ${tokenUserData.id}`)
      userData = tokenUserData
    } else {
      // Fall back to auth token validation (for backward compatibility)
      const { data: { user }, error: authError } = await supabase.auth.getUser(token)
      
      if (authError || !user) {
        return new Response(JSON.stringify({ error: 'Invalid token' }), {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        })
      }

      // Get user from users table using auth sub
      const { data: authUserData, error: authUserError } = await supabase
        .from('users')
        .select('id, email, name, sub')
        .eq('sub', user.id)
        .single()

      if (authUserError || !authUserData) {
        return new Response(JSON.stringify({ error: 'User not found' }), {
          status: 404,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        })
      }
      
      userData = authUserData
    }

    if (!userData) {
      return new Response(JSON.stringify({ error: 'User not found' }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    // Get user's "going" notifications
    // Use a raw query to get the event details
    const { data: notifications, error: notifError } = await supabase
      .from('friend_course_notifications')
      .select('event_id, created_at')
      .eq('user_id', userData.id)

    if (notifError) {
      console.error('Error fetching notifications:', notifError)
    }

    // Get the actual course dates
    // Parse event_id format: "kursnr_starttime_location" 
    // Example: "200-101_2025-11-03 18:45:00+00_Sprachheilschule, Turnhalle"
    const eventData = notifications?.map(n => {
      const eventId = n.event_id
      const parts = eventId.split('_')
      const kursnr = parts[0]
      
      // Find start_time (everything between kursnr and location)
      // Location is the last part, start_time is in the middle
      // We need to find where the location starts (it's always the last part after last underscore)
      const lastUnderscoreIndex = eventId.lastIndexOf('_')
      const start_time = eventId.substring(kursnr.length + 1, lastUnderscoreIndex)
      
      console.log(`Parsed event - kursnr: ${kursnr}, start_time: ${start_time}`)
      
      return {
        kursnr: kursnr,
        start_time: start_time,
        event_id: eventId
      }
    }) || []
    
    let events = []
    if (eventData.length > 0) {
      // Get kurs_termine based on kursnr and start_time
      for (const ed of eventData) {
        const { data: courseDates, error: coursesError } = await supabase
          .from('kurs_termine')
          .select('*')
          .eq('kursnr', ed.kursnr)
          .eq('start_time', ed.start_time)
        
        if (!coursesError && courseDates && courseDates.length > 0) {
          // Join with unisport_locations to get lat/lng
          for (const courseDate of courseDates) {
            let lat = null, lng = null
            
            if (courseDate.ort_href && courseDate.location_name) {
              // Try exact match first
              const { data: locationData } = await supabase
                .from('unisport_locations')
                .select('lat, lng')
                .eq('ort_href', courseDate.ort_href)
                .single()
              
              // If no exact match, try by location name
              if (!locationData) {
                const { data: nameLocationData } = await supabase
                  .from('unisport_locations')
                  .select('lat, lng')
                  .eq('name', courseDate.location_name)
                  .limit(1)
                  .single()
                
                if (nameLocationData) {
                  lat = nameLocationData.lat
                  lng = nameLocationData.lng
                }
              } else {
                lat = locationData.lat
                lng = locationData.lng
              }
            }
            
            events.push({ ...courseDate, lat, lng })
          }
        }
      }
    }

    // Generate iCal content
    let ical = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Unisport AI//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'X-WR-CALNAME:Unisport Meine Kurse',
      'X-WR-TIMEZONE:Europe/Zurich',
      'X-WR-CALDESC:Meine angemeldeten Sportkurse',
    ]

    if (events && events.length > 0) {
      for (const event of events) {
        if (!event.start_time) continue

        // Parse timestamps
        const startTime = new Date(event.start_time)
        const endTime = event.end_time ? new Date(event.end_time) : new Date(startTime.getTime() + 3600000)

        // Format for iCal: YYYYMMDDTHHMMSSZ
        const formatDate = (date: Date) => {
          const year = date.getUTCFullYear()
          const month = String(date.getUTCMonth() + 1).padStart(2, '0')
          const day = String(date.getUTCDate()).padStart(2, '0')
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          const seconds = String(date.getUTCSeconds()).padStart(2, '0')
          return `${year}${month}${day}T${hours}${minutes}${seconds}Z`
        }

        const uid = `${event.kursnr}_${event.start_time}_${userData.id}`
        
        const trainersStr = Array.isArray(event.trainers) ? event.trainers.join(', ') : event.trainers || 'N/A'
        
        // Get sport_name from sportkurse and sportangebote
        let sportName = 'Sportkurs'
        try {
          const { data: sportKurs } = await supabase
            .from('sportkurse')
            .select('offer_href, sportangebote(name)')
            .eq('kursnr', event.kursnr)
            .limit(1)
            .single()
          
          if (sportKurs && sportKurs.sportangebote) {
            sportName = sportKurs.sportangebote.name || 'Sportkurs'
          }
        } catch (error) {
          console.error('Error fetching sport name:', error)
        }
        
        // Get friends who are also going to this event
        const eventId = `${event.kursnr}_${event.start_time}_${event.location_name}`
        
        // Get friends attending the same event
        let friendAttendees: string[] = []
        try {
          // Get friendships
          const { data: friendships } = await supabase
            .from('user_friends')
            .select('*')
            .or(`requester_id.eq.${userData.id},addressee_id.eq.${userData.id}`)

          if (friendships && friendships.length > 0) {
            // Determine friend IDs
            const friendIds: string[] = []
            for (const friendship of friendships) {
              if (friendship.requester_id === userData.id) {
                friendIds.push(friendship.addressee_id)
              } else {
                friendIds.push(friendship.requester_id)
              }
            }

            if (friendIds.length > 0) {
              // Check which friends are also going
              const { data: friendNotifications } = await supabase
                .from('friend_course_notifications')
                .select('user_id, users!user_id(email)')
                .eq('event_id', eventId)
                .in('user_id', friendIds)

              if (friendNotifications) {
                // Extract email addresses
                for (const notif of friendNotifications) {
                  if (notif.users && notif.users.email) {
                    friendAttendees.push(notif.users.email)
                  }
                }
              }
            }
          }
        } catch (error) {
          console.error('Error fetching friends:', error)
        }
        
        // Start building event
        const eventLines = [
          'BEGIN:VEVENT',
          `UID:${uid}`,
          `DTSTAMP:${formatDate(new Date())}`,
          `DTSTART:${formatDate(startTime)}`,
          `DTEND:${formatDate(endTime)}`,
          `SUMMARY:${sportName}`,
          `LOCATION:${event.location_name || 'Unisport'}`,
          `DESCRIPTION:Trainer: ${trainersStr}`,
        ]

        // Add GEO coordinates if available (format: lat;long)
        if (event.lat && event.lng) {
          eventLines.push(`GEO:${event.lat};${event.lng}`)
        }

        // Add friend attendees if any
        if (friendAttendees.length > 0) {
          for (const email of friendAttendees) {
            eventLines.push(`ATTENDEE;RSVP=TRUE;CN=Freund:mailto:${email}`)
          }
        }

        eventLines.push(
          'STATUS:CONFIRMED',
          'SEQUENCE:0',
          'BEGIN:VALARM',
          'TRIGGER:-PT15M',
          'ACTION:DISPLAY',
          'DESCRIPTION:Erinnerung',
          'END:VALARM',
          'END:VEVENT'
        )

        ical.push(...eventLines)
      }
    }

    ical.push('END:VCALENDAR')

    const icalContent = ical.join('\r\n')

    return new Response(icalContent, {
      status: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'text/calendar; charset=utf-8',
        'Content-Disposition': 'inline; filename=unisport_meine_kurse.ics',
      },
    })
  } catch (error) {
    console.error('Error generating iCal:', error)
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
})

