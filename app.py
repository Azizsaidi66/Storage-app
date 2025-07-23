import hashlib
import pyodbc # type: ignore
from flask import Flask, request, render_template, redirect, session, url_for, send_file, flash
from azure.storage.blob import BlobServiceClient
from io import BytesIO

app = Flask(__name__)
app.secret_key = "keyazHKFHHhhklcfd46zefZD6D4Qpkfpz"

conn_key = "Driver=ODBC Driver 17 for SQL Server;Server=tcp:storage-app-server.database.windows.net,1433;DATABASE=storage-app-db;Initial Catalog=storage-app-db;Persist Security Info=False;Uid=azizsaidi66server;Pwd=Azizalaasaidi66;MultipleActiveResultSets=False;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

conn = pyodbc.connect(conn_key)
cursor = conn.cursor()

@app.route('/signup', methods=["GET", "POST"])
def auth():
    if session.get("user_id"):
        return render_template("home.html")
    else:
        if(request.method == "POST"):
            form_type = request.form.get("form_type")

            if form_type == "signup":
                username = request.form.get("username")
                email = request.form.get("email")
                password = request.form.get("password")
                if not username or not email or not password:
                    flash("please provide all infos !")
                    return render_template("auth.html")
                
                cursor.execute("SELECT * FROM Users WHERE username = ? OR email = ?", (username, email))
                rows = cursor.fetchone()
                if rows is not None:
                    flash("Account already exists !")
                    return render_template("auth.html")
                
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute("INSERT INTO Users (Username, Email, Password) VALUES(?, ?, ?)", (username, email, hashed_password))
                conn.commit()
                flash("Sign up succecfull please log in !")
                return render_template("auth.html")
            
            
            elif form_type == "login":
                email = request.form.get("email")
                password = request.form.get("password")
                if not email or not password:
                    flash("Please enter correct informations !")
                    return render_template("auth.html")
                
                cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
                user = cursor.fetchone()

                if user is None:
                    flash("User does not exist")
                    return render_template("auth.html")
                
                stored_pass = user[3]
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                if(stored_pass != hashed_password):
                    flash("Password incorrect !")
                    return render_template("auth.html")
                
                session["user_id"] = user[0]
                session["username"] = user[1]
                return redirect(url_for("home"))
        return render_template("auth.html")
    
@app.route('/logout')
def logout():
    flash("Logged out successfully !")
    session.clear()
    return redirect(url_for('home'))


connecting_key = "DefaultEndpointsProtocol=https;AccountName=myappstorage001;AccountKey=di7v4DsXxRjLo0Fx0/y6RQtaasrvg3VAvyXEygtWWDK0mSs0971kgb7azeXNFtHHvRknhs2gwMVD+ASttg5jTg==;EndpointSuffix=core.windows.net"
container_name = "upload"

blob_service_client = BlobServiceClient.from_connection_string(connecting_key)
container_client = blob_service_client.get_container_client(container_name)

@app.route('/', methods=['GET', 'POST'])
def home():
    user_id = session.get("user_id")
    if(user_id):
        prefix = f"{user_id}/"
        if request.method == 'POST':
            files = request.files.getlist('file')
            for file in files:
                blob_name = prefix + file.filename
                blob_client = container_client.get_blob_client(blob_name)
                blob_client.upload_blob(file, overwrite=True)
            return redirect(url_for('home'))

        blobs = container_client.list_blobs(name_starts_with=prefix)
        files = []
        for blob in blobs:
            files.append({
                'name': blob.name[len(prefix):],
                'size': round(blob.size / 1024, 3),  # in Kb
                'upload_time': blob.last_modified.strftime("%Y-%m-%d")
            })
        return render_template("index.html", files=files)
    else:
        return render_template("index.html", files=[])

@app.route('/download/<filename>')
def download_file(filename):
    prefix = f"{user_id}/" # type: ignore
    blob_name = prefix + filename
    try:
        blob_client = container_client.get_blob_client(blob=blob_name)
        stream = blob_client.download_blob()
        return send_file(BytesIO(stream.readall()), as_attachment=True, download_name=filename)
    except Exception:
        flash("Error downloading file.")
        return redirect(url_for('home'))

@app.route('/delete/<filename>')
def delete(filename):
    user_id = session.get("user_id")
    prefix = f"{user_id}/"
    blob_name = prefix+filename
    try:
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        flash("File deleted successfully !")
    except Exception:
        flash("Error while deleting file !")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)