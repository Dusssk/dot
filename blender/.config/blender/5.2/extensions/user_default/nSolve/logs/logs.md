![nSolve Logo](./images/ns_text.png)

___

[Nsolve](https://blendermarket.com/products/nsolve)

___

# 008

### Release Log Display
  - An icon for a changelog has been added to the topbar for nsolve / nsuite

## nSolve
  - Hide (244)
  - Bandolier Text subobject
    - Opt in (behavioral dropdown)
## nSuite (258)
  - "Edit Mode" icons
    - Bandolier edit mode format change to show icons instead of list
  - Script "suboption" custom (V1)

Bandolier Magnification 
  - Prop added to prefs
  
## Element: Banner
  - Banner is an attempt at a "beacon" system intended for interfacing and feedback in the future
  - Current version is a POC showing a complex concept but is subject to change

## Small Stuff
Analytics - text document export and processing based on tool use (optional opt in / experiemental)

___

# 007 

## nSolve
  Corner UI Adjustments (247)
   - Responsiveness adjustment
   - Priority reorder
  
  Analyze (255)
   - Behavioral dropdown options added
    - Flipped normals 
    - Statistics on ngon / tris

## Small Stuff
  Jump to nsolve when activated via the pie (242)
  nSolve
    - Bandolier Option (filter) return (257)
     - Previously broken via the bandolier transition
  Basic Tet (NSO) config added
  Preference cleanup (slight)
    - Expanded nsolve bandolier
  Options dropdown (slight)

___

# 006 

# Basic Features / Improvements 

  ## nSolve 
    Bandolier Mk2 
      - PNG icon conversion
    Merge  
      - Weld Parameter (240)
        - Weld post option added to behavior panel 
    Hard Bevel 
      - (show mesh toggle during use)
        - Mesh is now able to be left behind for post operations

  ## nSuite
    Customizable icon placement
      - Edit mode option via behavioral dropdown for nsuite (when in use)
      - Connected to persona system
        - Default persona

    Extended Assignment Availability
      - Custom tool support via geometry node creation 
      - Custom operator bandolier
        - 3 lists (nsuite, tools, custom)
      
    Behavioral Dropdown Pref added
      - Alt scroll toggle

## Small Stuff

  ### Bugfixes
    Hard Bevel - stop operation if no pairs (#250)
    Persona list format cleanup (minor)
      - No longer listing file extension as well (249)


```This release was intended to set the stage for the bandolier to be able to made into different shapes on the fly like tetris blocks and other unusual configurations. This required a massive rework of the bandolier system in the aims of making it more customizable. Hard bevel being able to show the mesh allows for analysis of failure which is more important than fluidity. The tool continues to get much needed attention.```

___

![nSolve Logo](./images/nSolve.png)

___

# 005

## nSolve 
  Pie Menu System
    - Alt + 1
    - Customizable in-tool experimental pie system (experimental, subject to change)
  
  Interface V1 (visual notification system)
    - Toggleable via settings dropdown
    - Experimental hud V1 
      - Animated transitions
        - Header / Subtext / Corner ticks
      - Custom Font Support
  
  Topbar Eye (single click)
    - nSuite to nSolve 

## nSuite
  Project Circle
    - [ALT] for cut through
  
  Mesh Cut
    - [CTRL + Z] undo support during tool use (234)
    - used during continuous use via the settings dropdown
  
  Inteface V1
    - Header Text v1 for select options
  

## Small Stuff
  - Bandolier hide during tool use

___

# 004

## nSolve 
  Join 
    - Extend to line (alt use)
    - Box select on no selection 
  
## nSuite
  Custom (NEW)
    - Custom command offering via D helper
    - Offering via + in helper
    - Basic command customization functionality
  
  Hard Loop
    - Multiple loop support on scroll / arrow / brackets
  
  Mesh Cut
    - Continuous toggle added to behavioral dropdown
  
## nFlow
  Suggest Poly
    - (NEW) Stable Offering - aims to be more stable than both systems in suggest caluclation.


## Small Stuff
  - Active tool icon use adjustment (slight)
  - Preference Added
    - Gizmo background color exposed (216)
    - Nflow retopo pref relaxed for ndraw (214)
  
  - nSuite 
    - Project Loop - multiple loop support (211)
  
  ### Bugfixes
    - nSolve
      - Join (etc) - Hidden Geo bug resolved (from camera video) (210)
        - Bounding box draw calc refinements (228) 

___

# 003

## nFlow 

  - Input section added under behavioral dropdown
  - Numbers to config swap added as disable default. 
    - No longer connected to alt + scroll
  - Merging radius added under snapping options
  
## nSuite
  Hard Loop
    - F9 Offerings expanded
    - Normalized config between alt + 4 option and gizmo launch
      ○ Ignore release confirm. Only press accepted
    - Pref to merge doubles into new loop
    - Object scale taken into account
  Project Loop
    - Tweak mode on tab added
    - Behavioral improvments
    - Scale independent behavior
    - Adjustments to root system improving compatibility
    - Tab into edit mode

## nSolve
  Slide
    - Context option dropdown
    - Multi-element option added
  Join
    - Extension unto line on use
  Rake (initial v1)
    - Individual vert extrude
    - Free Transform
    - Tab into edit mode

## Small Stuff
  - Pref cleanup slight
  - nFlow : ntx files added
    - Model.ntx
    - Uv.ntx
  
  ### Bugfixes
    - Nflow : Project shrinkwrap logic fix
    - nFlow : BVH Raytree error resolved
    - nSolve : Connect vert nmesh error
    - nSolve: nmesh system improvements 
      - util for projecting 3d vector in 2d region
      - Guard against non return, discard of edges behind view
      - Guard against nearest point being behind the view
    - nSolve : Out of region fix (slide)
    - nSolve : Bug resolved w/ bmesh free
  
  nSolve : Analyze - bug resolved w/ new file while active (202) 

___

# 002

## nSolve
  Merge 
    - At Center toggle added
      ○ Persona support
  Analyze
    - Z fighting improvments
    - Stability increase 
  nSolve Bandolier - Scale
    - Grabbing the move handle and pressing S scales. 
    - Helper reset button will reset the scale if needed

## Small Stuff
  - Examples removed from menus (for now) 
  - Alt + 4 >> Project Options 
    ○ Starts on LMB rather than on menu activate. 

  ### Bugfixes
    - Default bbox to none
    - NSO: Dissolve bug w/ mismatched vector
    - HOPS popup formalization resolution for Ctrl + K
      - Supportive as addon or extension

___

# 001 (initial release)

## Initial

![nSolve Logo](./images/nSolve.png)