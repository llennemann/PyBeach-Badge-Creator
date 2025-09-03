# ---------------------- IMPORTS ----------------------
import pandas as pd
import yaml
import re
from svglib.svglib import svg2rlg

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, HexColor, white, grey
from reportlab.graphics import renderPDF
from reportlab.pdfbase.pdfmetrics import stringWidth

# ---------------- HELPER FUNCTIONS ----------------
def return_fontsize_that_fits(badge_width, text, font_size):
    """
    Determines a fontsize for a line of text such that 
    it fits on one line on a badge of given width. 

    Args:
        badge_width (float): Badge width in reportlab points.
        text (string): Text to check. 
        font_size (int): Font size to try first.

    Returns:
        float: Font size. 
    """
    text_width = stringWidth(text, 'Helvetica', font_size)
    while text_width > badge_width:
        font_size -= 3
        text_width = stringWidth(text, 'Helvetica', font_size)
    return font_size


def standardize_pronouns(pronoun_str):
    """
    Standardizes and formats pronouns, into either: 
    He / Him, She / Hers, They / Them, or any combination of He, She & They. 

    Args:
        pronoun_str (string): String containing user inputted pronouns.

    Returns:
        string: Standardized pronouns
    """
    if "/" in pronoun_str:
        pronouns = pronoun_str.split("/")
    else:
        pronouns = [pronoun_str]

    pronouns = [pro.lower().strip() for pro in pronouns]
    final_list = []
    
    if 'he' in pronouns or 'him' in pronouns or 'his' in pronouns:
        final_list.append('he')
    if 'she' in pronouns or 'her' in pronouns or 'hers' in pronouns:
        final_list.append('she')
    if 'they' in pronouns or 'them' in pronouns or 'theirs' in pronouns or 'their' in pronouns:
        final_list.append('they')

    # only she:
    if len(final_list) == 1:
        if final_list[0] == 'he':
            return 'He / Him'
        elif final_list[0] == 'she':
            return 'She / Hers'
        else:
            return 'They / Them'
    else:
        final = ""
        for item in final_list:
            final += item.capitalize() + " / "
        return final[:-2]


def format_pronouns(pronoun_str):
    """
    Formats pronouns where each word is capitalized and 
    separated by " / ". 

    Args:
        pronoun_str (string): String containing user inputted pronouns.

    Returns:
        string: Formatted pronouns
    """
    cleaned = " ".join(pronoun_str.split())
    cleaned = re.sub(r"\s*/\s*", " / ", cleaned)
    formatted = " ".join(word.capitalize() for word in cleaned.split())
    return formatted

# ------------------- PROCESSING -------------------
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

df = pd.read_csv(config["file_path"])

df_filtered = df[df['Ticket'] != 'Donate to PyBeach']  # ignore ticket type = Donate to PyBeach
df_filtered = df[df['Photo opt-out'].notna()]          # ignore rows without photo opt-out values
df_filtered['Attendee'] = 'Attendee'

df_filtered = df_filtered.reset_index()

# ------------------- CREATE PDFS -------------------
badge_width = 4 * 72                                   # badge size: 4"x2 7/8" 
badge_height = 2.875 * 72 
width, height = LETTER
badge_xys = [                                          # placement for the 6 badges on 1 page with padding between
    (10, 565),   
    (316, 565), 
    (10, 338),   
    (316, 338), 
    (10, 111),   
    (316, 111)  
]

output_path = "badges_0.pdf"                           # starting canvas
c = canvas.Canvas(output_path, pagesize=LETTER)

badge_count = 0
for index, row in df_filtered.iterrows():
    if badge_count == 6:                               # start a new sheet of badges
        c.save()
        print(f"PDF saved to {output_path}")
        output_path = "badges_" + str(index) + ".pdf"
        c = canvas.Canvas(output_path, pagesize=LETTER)
        c.setFillColor(black)
        badge_count = 0
    name = row["What name would you like printed on your badge?"]
    if pd.isna(name):
        print(f'Error with row {index}: name is missing a value.')
        continue
    
    x = badge_xys[badge_count][0]                       # top left point for the badge
    y = badge_xys[badge_count][1]
    
    if row['Photo opt-out'] == 'Opt-out':               
        drawing = svg2rlg(config['photo_opt_out_icon'])
        logo_size = 50
        scale = min(logo_size / drawing.width, logo_size / drawing.height)
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)
        renderPDF.draw(drawing, c, x + 4, y + badge_height - 50)
    
    pronouns_option = row['Would you like your pronouns printed on your badge?']
    if pd.isna(pronouns_option) or pronouns_option == 'Yes':
        pronouns = row['Pronouns']
        if not pd.isna(pronouns) and pronouns != "-":
            c.setFont("Helvetica", 13)
            c.setFillColor(black)
            c.drawRightString(x + badge_width - 4, y + badge_height - 8, pronouns)

    drawing = svg2rlg(config['logo_icon'])
    logo_size = 72
    scale = min(logo_size / drawing.width, logo_size / drawing.height)
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)
    renderPDF.draw(drawing, c, x + (badge_width - logo_size) / 2, y + badge_height - logo_size - 10)

    # Company name should only be printed on Corporate and Early Bird Corporate badges
    typ = row["Ticket"]
    title = row["Ticket Job Title"]
    company = ""
    if typ == 'Early Bird Corporate' or typ == 'Corporate':
        company = row["Ticket Company Name"]
        if not pd.isna(title):
            company = f"{title}, " + company
    else:
        if not pd.isna(title):
            company = f"{title} " + company

    if company == "":
        name_y = y + badge_height - 125
    else:
        name_y = y + badge_height - 110
    
    cleaned_name = re.sub(r"\s+", " ", name).strip()                      # clean up spacing in name 
    font_size = return_fontsize_that_fits(badge_width, cleaned_name, 20)
    c.setFont("Helvetica-Bold", font_size)
    c.setFillColor(black)
    c.drawCentredString(x + badge_width / 2, name_y, cleaned_name)        # print in the middle if no job title/company

    if company != "":
        job_font_size = return_fontsize_that_fits(badge_width, company, 14)
        c.setFont("Helvetica", job_font_size)
        c.setFillColor(black)
        c.drawCentredString(x + badge_width / 2, y + badge_height - 130, company)

    event = config['event_name']
    c.setFillColor(grey)
    c.setFont("Helvetica", 13)
    c.drawCentredString(x + badge_width / 2, y + badge_height - 165, event)

    if not pd.isna(row["Attendee"]):
        ribbon_height = 25
        c.setFillColor(HexColor("#337ab7"))
        c.rect(x, y + 5, badge_width, ribbon_height, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(x + badge_width / 2, y + 12, row["Attendee"])
    else:
        print(f'Warning: {name} does not have a value for Attendee column.')
    badge_count += 1

c.save()                                                 # save any remaining canvas
print(f"PDF saved to {output_path}")