# Master Data Management System

## 📌 Project Overview

The Master Data Management System is a web-based application developed using Python and Flask. It provides a centralized platform for managing master data efficiently.

The system allows users to insert, update, delete, search, and view master data through a web interface.

## 🚀 Features

- Add new master data
- Update existing records
- Delete records
- Search and filter master data
- View all available records
- Bulk insert data using Excel files
- Download search results
- Excel-based data import
- Web-based user interface

## 🛠️ Technologies Used

- Python
- Flask
- HTML5
- CSS3
- JavaScript
- Excel / XLSX
- SQLite / Database

## 📂 Project Structure

```text
Master-Data-Management-System/
│
├── demo.py
├── .gitignore
│
└── item_master/
    ├── app.py
    ├── config.py
    ├── requirements.txt
    │
    ├── src/
    │   ├── __init__.py
    │   ├── database.py
    │   ├── pharma.py
    │   └── routes.py
    │
    ├── static/
    │   ├── script.js
    │   ├── styles.css
    │   └── image/
    │
    └── templates/
        ├── index.html
        ├── insert.html
        ├── update.html
        ├── delete.html
        ├── search.html
        ├── view_all.html
        └── ...
