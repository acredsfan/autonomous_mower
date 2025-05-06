# Autonomous Mower UI Testing Checklist

## Instructions

- Use this checklist when testing the web UI of the autonomous mower
- Mark items with "✅" (working), "❌" (not working), or "⚠️" (partially working)
- Add notes about specific issues or behaviors observed

## Dashboard Tab

- [⚠️] Dashboard page loads correctly
- [❌] Battery status indicator shows current level
- [❌] GPS status displays fix information correctly
- [❌] Clock shows correct time and updates
- [❌] Sensor readings display and update
- [❌] System status card shows current state
- [❌] Quick control buttons respond to clicks
- [❌] Map preview loads and displays mower location
- [❌] System information section displays correct data
- [❌] Error alerts display when errors occur

## Map Tab - Basic Functionality

- [✅] Map tab loads without errors
- [✅] Map view renders correctly (satellite/standard)
- [❌] Map loads at correct location
- [❌] Toggle Street button works
- [✅] Search address field works
- [✅] Map zooming works
- [✅] Map panning works

## Map Tab - Drawing & Configuration

- [✅] Draw Yard Boundary tool can be selected
- [✅] Can draw a boundary by clicking points on map
- [✅] Drawn boundary displays correctly
- [❌] User receives feedback when boundary is saved
- [✅] Set Home Location tool works
- [❌] User receives feedback when home location is set
- [✅] Add No-Go Zone tool works
- [✅] Can draw no-go zones on the map
- [❌] User receives feedback when no-go zones are saved
- [❌] Clear All button removes all drawn elements
- [❌] User receives feedback when map is cleared
- [❌] Map loads with previously saved markers when returning to map tab

## Map Tab - Pattern Generation

- [❌] Pattern selection buttons work (changing active pattern)
- [❌] Parallel pattern can be selected
- [❌] Spiral pattern can be selected
- [❌] Zigzag pattern can be selected
- [❌] Checkerboard pattern can be selected
- [❌] Diamond pattern can be selected
- [❌] Waves pattern can be selected
- [❌] Concentric pattern can be selected
- [❌] Pattern settings can be adjusted (spacing, angle, overlap)
- [❌] Generate Pattern button works
- [❌] Generated pattern displays on map
- [❌] User receives feedback when pattern is generated successfully

## Control Tab

- [⚠️] Control page loads correctly
- [❌] Forward movement button works
- [❌] Backward movement button works
- [❌] Left turn button works
- [❌] Right turn button works
- [❌] Stop button works and halts all movement
- [❌] Speed slider adjusts movement speed
- [❌] Blade control buttons work (on/off)
- [❌] Camera feed displays (if applicable)

## Diagnostics Tab

- [✅] Diagnostics page loads correctly
- [❌] Sensor data displays and updates
- [❌] System logs can be viewed
- [❌] Hardware status information is shown
- [❌] Error history is available
- [❌] Diagnostic test buttons function correctly
- [❌] System resource usage displays correctly (CPU, memory)

## Settings Tab

- [✅] Settings page loads correctly
- [ ] Mowing settings can be viewed and changed
- [ ] Navigation settings can be viewed and changed
- [ ] Safety settings can be viewed and changed
- [ ] System settings can be viewed and changed
- [ ] Language can be changed
- [ ] Units can be changed (imperial/metric)
- [ ] Settings save correctly when changed
- [ ] User gets feedback when settings are saved

## General UI Behavior

- [ ] Page navigation works (can navigate between all tabs)
- [ ] Connection status indicator shows correct state
- [ ] Responsive design works (UI adapts to different screen sizes)
- [ ] Error handling shows user-friendly messages
- [ ] Loading spinners display during long operations
- [ ] Toast notifications appear and dismiss correctly
- [ ] UI updates in real-time with mower status changes

## User Feedback Enhancement Priorities

- [ ] Add success toast notification when saving yard boundaries
- [ ] Add success toast notification when setting home location
- [ ] Add success toast notification when saving no-go zones
- [ ] Add success toast notification when generating patterns
- [ ] Add loading indicators during map operations
- [ ] Add confirmation dialogs for destructive actions (like Clear All)
- [ ] Add error notifications with specific details when operations fail
