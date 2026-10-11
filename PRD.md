# My Product Requirements Document
  - This is the PRD for creating a webpage to track members registration 

## Strict Guidelines - Must follow 
 - Do not make any assumption on the requirements , stick to the ask and always ask me when in confusion 
 - Iterate on the questions till you get all the answers before writing the first code 
 - Create a word document on project requirements  
 - Create an interactive architecture map of the overall code 
 - Create an simple video file explaining the project 

 
## 1. What is this?
 - A web page to track , audit and predict members registrations 

## 2. Who is it for?
 - Marketing teams to measure and send marketing emails to dirve mebers registations 

## 3. What problem does it solve?
 - Digital engagment in a health care app 

## 4. What must it do?
 - Combine all data under the "Data" folder in one single CSV file - Call this as Master.CSV
 - Create a simple webpage which shows user registration statictics 
 - Make the page interactive to allow user to see registration stats on a certain date and time 
 - Create 3D visuals to measure user registrations 
 - Allow user to run and download simple reports 
      -- List of all members who are not registered 
	  -- Registration stats in a day 
	  -- Registration speread over the last 6 months 
 - Layout of the webpage 
   -- Left side with 3 options 
      -- Option 1 : View registration stats 
      -- Option 2 : mmeber reach out 
      -- Option 3 : reporting 	

   - Right Side of web page for Option 1
     -- Input should be a Month , Match this to month in the registration_date field 
     -- Multiple visualization methods in 2D and 3D options ( Bar , graph , heat map ) and visualize registration activity 
     -- Notate low registration days and high registration days 
	 -- Use Soft colors with soft tone . Hight anamolies using strong colors 
     -- Ability to download graphs 
	 
    - Right Side of web page for Option 2
	 -- Allow input fields to query member id using SSN or member_id 
	 -- Gather member details from CSV files under Data folder ( search Master.csv) 
	 -- Provide an Input text box for a Marketing member to provide outreach message ( provide an option for outrech template ) 
	 -- Submite button to send the email 
	 
     - Right Side of web page for Option 3
	 -- Rich reporting module to report on 
	    -- Member registration in a month ( compare this to the registration_date ) 
		-- Query on registration_status and month 
		-- Query on relationship_code 
		-- Abillity to download CSV files 

## 5. What should it NOT do?
 - No Logins or security module 
 


## 6. How should it feel?
 - UI/UX should have blue theme 
 - Keep the Color tone light , Use Strong colors to show anamolies 

