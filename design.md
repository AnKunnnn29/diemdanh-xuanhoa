# Design — Giáo Xứ Xuân Hoà

Updated 15 October 2026. The user approved simplifying the existing interface for
older catechists and people who use technology infrequently. This revision is
implemented locally. Class staffing is imported from the supplied 2026–2027
Word plan, with the user's decisions for the two DB classes and HKII staffing.

## Users and daily work

Catechists choose their class, record attendance, look up a child's family contact,
enter grades, handle leave requests, and download a completed class workbook.
Managers retain access to class records, teacher assignments, reports, backups,
configuration and school-year preparation through the secondary navigation.

After an explicit successful login (including the mandatory first password
change), the route is #home, with the illustrated church-and-doves welcome.
Restored sessions preserve their requested route. The working hub is #start.
Its four large actions are attendance today, find a
child, enter grades and download the class book. Home and today's work are the
first two navigation links. Native disclosures group class work, follow-up and
staff, and administration; the group containing the current route opens itself.
Mobile has four persistent bottom actions and a menu for other tasks. The chosen
class persists on the device and is shown only on screens that use it; it is not an
authorization boundary.

The first section after the full-screen home illustration introduces the parish,
its diocese and deanery, the actual school-year theme and class totals. It links
to today's work and staff assignments. The teacher page shows actual Excel
names, classroom locations and separate HKII notes, with class/name search and
assignment status filters. A mismatch between an Excel name and the linked
account requires an explicit choice before saving; it cannot silently erase the
name from the workbook. See WORKSPACE-FLOW-2026-10-15.md for the source mapping.

## Visual direction and assets

The supplied parish logo, cream surfaces, dark ink and green primary actions stay.
Nunito is the working-interface font. Body text is 18px; primary controls have at
least 52px height. Use the default text and control sizes; the Chữ lớn toggle was removed at the user’s request.
Working pages use restrained borders and shadows, clearer labels and fewer
competing cards. Focus indicators, native controls and dialogs remain visible.

The public introduction remains at #home. Its existing playful educational
direction came from https://uupm.cc/demo/educational-platform: rounded Baloo 2
display type, pastel accents and clay cards. Self-hosted Nunito and Baloo 2 have
OFL licenses and Vietnamese glyph support. No new fonts, assets, animations,
frameworks or dependencies were introduced for this usability revision.

## Task flows

Attendance requires an explicit class/date/activity before showing recording
controls. Steps read Choose session → Record attendance → Review → Download.
Ending a session retains the backend preview and pending-request checks. The
finished screen shows the saved result and a download action. No future date can
be selected for a presence record through this flow.

Leave and weekday transfers use a three-step dialog: child/type, dates/activity,
review/reason. Existing approval, calendar and same-week rules remain enforced.
Mobile grades show one selected child; the edit dialog starts with one score
category and can expand to all categories. Saving preserves other input values,
including P, zero and blanks, and retains version conflict checks.

Class download works independently of attendance sessions. Multi-class/session
exports, configuration and other advanced operations are available in disclosures.
Optional family fields during intake are grouped without removing them.

## Data and content honesty

Working screens use the actual Excel catalog through the local bridge: 20 class
books in the configured 2026–2027 dataset. Counts and student identities come from
the API, not illustrative data. Profiles, grades, teachers, care, requests and
workbook management are implemented modules. Exports are real .xlsm workbooks
with the existing VBA and formulas preserved by the established backend.

Marketing stories remain explicitly illustrative. Cloud hosting, public 4G access,
Drive synchronization and individual account permissions are not claimed here.
The class selector and text-size setting are device preferences only.

## Implementation and verification

Login and password forms now share the full-screen parish night illustration,
without the GLV character/model. The church retains its twin spires; a detached
campanile with an open belfry, bronze bell, clock, shadow and its own steps stands
to its right, separated by visible courtyard space. It sits outside the church's
animated group. Portrait landing recomposes the two buildings to keep both in
frame; login preserves its wider illustration above the form. Desktop places a readable cream form beside the church; mobile stacks
the illustration above the form and permits natural scrolling. Login inputs
do not auto-focus on mobile. Required password changes cannot be skipped;
optional changes can return to the previous working page. The original auth,
autocomplete and password policies remain. A fresh successful login restarts the
landing entrance, while auth/password form changes preserve the ambient phase.
`src/auth-scene.css` scopes these styles; `npm run test:motion` now verifies the
church login instead of the retired mascot interactions.

The welcome hero uses original inline SVG artwork in `src/welcome-scene.js`,
styled by `src/welcome-scene.css`. Its evening green/gold palette is scoped to
the hero through named tokens; the surrounding cream parish theme stays.
The welcome fills the viewport edge to edge with no separate navigation bar,
border or rounded frame above it. The top-left identity pairs the original logo
with Giáo xứ Xuân Hoà, Giáo phận Xuân Lộc and Giáo hạt Tân Mai. Larger type uses
a consistent hierarchy for identity, headline and entry action. Five doves fly
from the lower-left corner into the sky above the church in under five seconds,
then remain there, alternating wingbeat bursts with long glides. Two distant
birds are smaller, translucent and slower. Eight tiny dust motes appear only
during the entrance. Their anchors
adapt on resize, keeping the flock clear of the logo, title and entry action.
Portrait artwork reserves sky space even on short phones; landscape keeps the
church towers inside the frame. There are no replay controls or footer labels.
The moon loops every 8 seconds (16px sideways, 26px upwards, 3.5% scale);
the church loops every 10 seconds (2px sideways, 8px upwards, 1.8% scale).
Both alternate eased outward and return legs to turn smoothly. All ambient
effects preserve their phase across normal data refreshes.
Six stars twinkle at different phases; the halo breathes on a six-second cycle,
with a separate warm sanctuary glow. Gold text uses a static tonal gradient and
a counter-moving highlight that leaves the letters in place. Text enters once;
the gold glass button keeps a strong contrast, keyboard focus and a short hover
reflection. Fine mouse pointers add a bounded 2–8px parallax to the artwork;
touch interaction and the text remain stable. A static two-layer cream wave
joins the hero to the existing content. Below-fold sections reveal once on
intersection, and focusing a control immediately shows its entire card.
WAAPI uses transform/opacity, pauses offscreen or in hidden tabs,
and is cancelled on route changes. Reduced motion leaves the static church;
unavailable WAAPI leaves the entry action usable.
Background refreshes do not repeat the entrance. The artwork is an illustrative
Catholic church, not a claimed architectural reconstruction of Xuân Hoà.

`src/welcome-svg-motion.js` retains the vector artwork but wraps moving SVG
groups in tightly bounded HTML boxes inside SVG foreignObjects. This avoids
SVG layout/paint invalidation during each transform. A two-second Edge headless
sample at 1440×900 reported zero repeated layout or paint events after this
change (the earlier SVG-group version reported 286 layouts and 572 paints).
This is a local desktop measurement, not a device-wide FPS guarantee.
`src/welcome-reveals.js` handles the independent visibility of below-fold cards.

Mobile action alignment, 15 October 2026: `src/mobile-ui.css` is the final
stylesheet layer for widths below 640px. Related actions share full-width rows;
short choices use equal columns. Semester controls have two equal term buttons
and a full-width annual-summary button, with content-driven height. Button labels
can wrap without clipping; table row actions retain their width inside the
existing horizontally scrolling tables. Existing colours, fonts, motion,
desktop layouts, native controls and business rules remain in use.

Checked 15 routes at 320, 375, 390, 414, 768 and 1440px. Mobile action groups were
measured for consistent widths/heights, clipped content and touch targets;
the existing layout suite also verified dialog focus return and bottom tabs.

tokens.css supplies shared type, control and color values. src/easy-ui.css is the
base usability layer for working screens, after the existing playful styles.
src/easy-ui.js supplies the start screen, attendance setup, grade field selector
and request wizard. Existing route and backend contracts remain available.

Browser checks use copied real workbooks for writes. Attendance, leave approval,
session closing, class download and grade entry were exercised. The existing
portable-grade regression checks cached results, P/zero/blanks and stale edits.
All twelve routes were checked at widths 320, 375, 414, 768 and 1440, including
keyboard focus return and bottom-navigation visibility. Desktop/mobile screenshots
were inspected. Direct observation with older catechists is still a future usability
check; automated checks do not establish that result.
