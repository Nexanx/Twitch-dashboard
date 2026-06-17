from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import glob

app = Flask(__name__)
DATA_DIR = 'data'

CUSTOM_GAME_ICONS = {
    "World of Warcraft": "https://upload.wikimedia.org/wikipedia/commons/e/eb/WoW_icon.svg", 
    "Path of Exile 2": "https://cdn2.steamgriddb.com/icon_thumb/c6f27990d7b1e2d00b1fcfdf7bfca28f.png",    
    "Gothic 1 Remake": "https://cdn2.steamgriddb.com/icon_thumb/06908932bbf6e2930a902e9597fa5e58.png" 
}

def optional_csv_value(row, column):
    if column not in row or pd.isna(row[column]):
        return None

    value = row[column]
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value)

@app.route('/')
def index():
    csv_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
    dates = sorted(list(set([os.path.basename(f).replace('.csv', '') for f in csv_files])), reverse=True)
    
    if not dates and os.path.exists(os.path.join(DATA_DIR, 'twitch_dynamic_dataset.csv')):
        dates = ['twitch_dynamic_dataset']
        
    games = ["World of Warcraft", "Path of Exile 2", "Gothic 1 Remake"]
    return render_template('index.html', dates=dates, games=games)

@app.route('/api/graph')
def get_graph_data():
    date_file = request.args.get('date')
    game = request.args.get('game')
    
    if not date_file or not game:
        return jsonify({"error": "Brak parametrów"}), 400

    filepath = os.path.join(DATA_DIR, f"{date_file}.csv")
    if not os.path.exists(filepath):
        return jsonify({"game": game, "languages": []})

    df = pd.read_csv(filepath)
    df_filtered = df[df['game_name'].str.lower() == game.lower()]

    if df_filtered.empty:
        return jsonify({"game": game, "languages": []})

    fallback_box_art = df_filtered.iloc[0]['game_box_art_url'] if 'game_box_art_url' in df_filtered.columns else ""
    
    matched_icon = None
    for k, v in CUSTOM_GAME_ICONS.items():
        if k.lower() == game.lower():
            matched_icon = v
            break
            
    final_box_art = matched_icon if matched_icon else fallback_box_art

    result = {
        "game": game,
        "box_art_url": final_box_art,
        "languages": []
    }

    grouped = df_filtered.groupby('language')
    for lang, group in grouped:
        top_streamers = group.sort_values('viewer_count', ascending=False)
        
        streamers_list = []
        for _, row in top_streamers.iterrows():
            uptime = int(row['uptime_minutes']) if pd.notna(row['uptime_minutes']) else 0
            avatar = str(row['profile_image_url']) if 'profile_image_url' in row and pd.notna(row['profile_image_url']) else ""
            
            streamers_list.append({
                "user_name": str(row['user_name']),
                "viewer_count": int(row['viewer_count']),
                "uptime": uptime,
                "profile_image_url": avatar,
                "avg_viewers_30d": optional_csv_value(row, 'avg_viewers_30d'),
                "followers_gained_30d": optional_csv_value(row, 'followers_gained_30d')
            })
            
        result["languages"].append({
            "lang": str(lang).upper(),
            "streamers": streamers_list
        })

    return jsonify(result)

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(debug=True)
