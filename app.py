import os
import requests
from fpdf import FPDF
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import re

# Function to get problem details from LeetCode
def get_problem_details(url):
    slug = url.split('/')[4]  # Extract slug from URL (e.g., 'two-sum')
    graph_url = "https://leetcode.com/graphql"
    headers = {'Content-Type': 'application/json'}
    query = {
        "operationName": "questionData",
        "variables": {"titleSlug": slug},
        "query": """
            query questionData($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    title
                    content
                }
            }
        """
    }
    response = requests.post(graph_url, json=query, headers=headers)
    if response.status_code == 200:
        data = response.json()
        question = data['data']['question']
        return question['title'], question['content']
    else:
        raise Exception("Error fetching data from LeetCode API")

# Function to format constraints dynamically (e.g., 10^4 -> 10⁴)
def format_constraints(text):
    superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', 
                       '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻'}
    
    def replacer(match):
        base, power = match.groups()
        superscript = ''.join(superscript_map.get(char, char) for char in power)
        return f"{base}{superscript}"
    
    return re.sub(r'(\d+)\^([-+]?\d+)', replacer, text)

# Function to clean and format problem content
def clean_and_format_content(content):
    soup = BeautifulSoup(content, 'html.parser')
    for sup in soup.find_all('sup'):
        sup.string = f"^{sup.string}"  # Replace <sup> tags with caret notation
    clean_content = soup.get_text()  # Strip all remaining HTML tags
    clean_content = format_constraints(clean_content)  # Format superscripts
    return clean_content

# Function to download images from problem content
def download_images(content, problem_number):
    soup = BeautifulSoup(content, 'html.parser')
    images = soup.find_all('img')
    image_paths = []
    for idx, img_tag in enumerate(images):
        img_url = img_tag.get('src')
        if not img_url.startswith('http'):
            img_url = f"https://leetcode.com{img_url}"
        try:
            response = requests.get(img_url, stream=True)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img_path = f"problem_{problem_number}_img_{idx + 1}.jpg"
                img = img.convert("RGB")
                img.save(img_path, format='JPEG')
                image_paths.append(img_path)
        except Exception as e:
            print(f"Error downloading image from {img_url}: {e}")
    return image_paths

# Function to create a combined PDF with interlinking
def create_combined_pdf_with_links(problems, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_font('DejaVu', '', 'Ubuntu-Regular.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'Ubuntu-Bold.ttf', uni=True)

    # Create the Index Page
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 22)
    pdf.cell(0, 10, "Index Of Problems", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font('DejaVu', '', 18)
    category_count = 0
    problem_serial = 0

    category_links = {}  # Store links for categories
    problem_links = {}   # Store links for problems

    for problem_number, (title, _, _, url) in enumerate(problems, start=1):
        if url is None:  # Category marker
            category_count += 1
            problem_serial = 0
            link = pdf.add_link()
            category_links[category_count] = link
            pdf.set_font('DejaVu', 'B', 18)
            pdf.set_text_color(0, 0, 255)  # Blue text for category name
            pdf.cell(0, 10, f"{category_count}. {title}", ln=True, link=link)
        else:
            problem_serial += 1
            link = pdf.add_link()
            problem_links[problem_number] = link
            pdf.set_font('DejaVu', '', 16)
            pdf.set_text_color(0, 0, 0)  # Black text for problems
            pdf.cell(0, 10, f"  {problem_serial}. {title}", ln=True, link=link)

    # Add pages for each problem
    category_count = 0
    problem_serial = 0

    for problem_number, (title, content, image_paths, url) in enumerate(problems, start=1):
        if url is None:  # Category marker
            category_count += 1
            pdf.add_page()
            pdf.set_link(category_links[category_count])  # Set link to this page
            pdf.set_font('DejaVu', 'B', 30)
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 150, txt=title, ln=True, align='C')
            pdf.set_text_color(0, 0, 0)
            continue

        problem_serial += 1
        pdf.add_page()
        pdf.set_link(problem_links[problem_number])  # Set link to this page
        pdf.set_font('DejaVu', 'B', 21)
        pdf.set_text_color(0, 0, 255)
        pdf.cell(0, 10, txt=title, ln=True, align='C')
        pdf.ln(5)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font('DejaVu', '', 18)
        pdf.multi_cell(0, 7, content)

        if image_paths:
            pdf.add_page()
            pdf.set_font('DejaVu', 'B', 14)
            pdf.cell(0, 10, f"Images for {title}:", ln=True, align='C')
            pdf.ln(5)

            for idx, img_path in enumerate(image_paths):
                if os.path.exists(img_path):
                    img_width, img_height = Image.open(img_path).size
                    page_width = 190  # Max width for PDF
                    page_height = 297  # Max height for PDF
                    margin = 10  # Top and bottom margin
                    available_height = page_height - pdf.get_y() - margin

                    scale = page_width / img_width
                    scaled_width = page_width
                    scaled_height = img_height * scale

                    if idx == len(image_paths) - 1 and scaled_height > available_height:
                        scale = available_height / img_height
                        scaled_width = img_width * scale
                        scaled_height = available_height

                    pdf.image(img_path, x=10, y=pdf.get_y(), w=scaled_width, h=scaled_height)
                    pdf.ln(scaled_height + 5)

    pdf.output(output_path)
    print(f"PDF saved successfully at: {output_path}")

# Main function
def main():
    links_file = "links.txt"
    if not os.path.exists(links_file):
        print(f"File {links_file} not found. Please create it and add LeetCode URLs.")
        return
    with open(links_file, "r") as file:
        urls = [line.strip() for line in file.readlines() if line.strip()]
    if not urls:
        print(f"No URLs found in {links_file}. Please add LeetCode URLs.")
        return

    output_path = "LeetCode_Problems.pdf"
    problems = []
    current_category = None

    for line in urls:
        if line.startswith("~"):
            current_category = line[1:].strip()  # Extract category name
            problems.append((current_category, None, None, None))  # Add category as a marker
            continue
        
        try:
            print(f"Processing: {line}")
            title, content = get_problem_details(line)
            formatted_content = clean_and_format_content(content)
            image_paths = download_images(content, len(problems))  # Use problem length as index
            problems.append((title, formatted_content, image_paths, line))
        except Exception as e:
            print(f"Error processing {line}: {e}")
            continue

    if problems:
        create_combined_pdf_with_links(problems, output_path)
    else:
        print("No problems were successfully processed.")

if __name__ == "__main__":
    main()
