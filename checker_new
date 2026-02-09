#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>
#include <glib/gstdio.h>
#include <stdio.h>

#define CONFIG_FILENAME "ignored_files.txt"

// --- CSS & Theme ---
void apply_dark_theme() {
    GtkSettings *settings = gtk_settings_get_default();
    g_object_set(settings, "gtk-application-prefer-dark-theme", TRUE, NULL);
    g_object_set(settings, "gtk-menu-images", TRUE, NULL);

    GtkCssProvider *provider = gtk_css_provider_new();
    const char *css =
        "window { background-color: #1e1e1e; color: #cccccc; }"
        "treeview { background-color: #252526; color: #cccccc; }"
        "treeview:selected { background-color: #094771; color: #ffffff; }"
        "button { background-color: #3c3c3c; color: #ffffff; border: 1px solid #2d2d2d; }"
        "button:hover { background-color: #505050; }"
        "header { background-color: #2d2d2d; color: #cccccc; }"
        "menu { background-color: #2d2d2d; color: #cccccc; }"
        "menuitem { color: #cccccc; }"
        "menuitem:hover { background-color: #094771; color: #ffffff; }"
        "entry { background-color: #3c3c3c; color: #ffffff; border: 1px solid #474747; }";

    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(gdk_screen_get_default(),
                                              GTK_STYLE_PROVIDER(provider),
                                              GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
}

// --- Data Structures ---
typedef struct {
    char *full_path;
    char *name;
    char *markup;
    char *checksum;
    gboolean has_multi_space; 
    gboolean has_bad_format;  
    gboolean is_ignored;
} FileItem;

GPtrArray *file_list = NULL;
GHashTable *ignored_set = NULL;
char *current_root = NULL;
GtkWidget *tree_view;
GtkTreeViewColumn *col_name;
GtkCellRenderer *rend_name;

// --- Helpers ---
char* compute_checksum(const char *path) {
    return g_compute_checksum_for_string(G_CHECKSUM_MD5, path, -1);
}
gboolean is_open_bracket(gunichar c) { return c == '[' || c == '(' || c == '{'; }
gboolean is_close_bracket(gunichar c) { return c == ']' || c == ')' || c == '}'; }
gboolean is_space(gunichar c) { return c == ' '; }

void free_item(gpointer data) {
    FileItem *item = (FileItem *)data;
    g_free(item->full_path);
    g_free(item->name);
    g_free(item->markup);
    g_free(item->checksum);
    g_free(item);
}

char* try_fix_spaces(const char *name) {
    if (!strstr(name, "  ")) return NULL;

    GRegex *regex = g_regex_new(" {2,}", 0, 0, NULL);
    char *result = g_regex_replace_literal(regex, name, -1, 0, " ", 0, NULL);
    g_regex_unref(regex);
    return result;
}

// --- Config ---
void save_config() {
    FILE *f = fopen(CONFIG_FILENAME, "w");
    if (!f) return;
    GHashTableIter iter;
    gpointer key, value;
    g_hash_table_iter_init(&iter, ignored_set);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
        fprintf(f, "%s\n", (char*)key);
    }
    fclose(f);
}

void load_config() {
    FILE *f = fopen(CONFIG_FILENAME, "r");
    if (!f) return;
    char buffer[128];
    while (fgets(buffer, sizeof(buffer), f)) {
        g_strstrip(buffer);
        if (strlen(buffer) > 0) g_hash_table_add(ignored_set, g_strdup(buffer));
    }
    fclose(f);
}

// --- Markup Generator ---
char* generate_markup(const char *name, gboolean *out_multi, gboolean *out_bad, gboolean is_ignored) {
    GString *str = g_string_new("");
    const char *p = name;
    *out_multi = FALSE;
    *out_bad = FALSE;

    if (is_ignored) {
        char *esc = g_markup_escape_text(name, -1);
        g_string_append_printf(str, "<span foreground='#888888'>%s</span>", esc);
        g_free(esc);
        return g_string_free(str, FALSE);
    }

    while (*p) {
        gunichar curr = g_utf8_get_char(p);
        const char *next_p = g_utf8_next_char(p);
        gunichar next = *next_p ? g_utf8_get_char(next_p) : 0;

        gboolean bad_close = is_close_bracket(curr) && next != 0 && !is_space(next) && next != '.' && !is_close_bracket(next);
        gboolean bad_open = !is_space(curr) && !is_open_bracket(curr) && is_open_bracket(next);

        if (bad_close || bad_open) {
            *out_bad = TRUE; 
            char *curr_utf8 = g_ucs4_to_utf8(&curr, 1, NULL, NULL, NULL);
            char *next_utf8 = g_ucs4_to_utf8(&next, 1, NULL, NULL, NULL);
            char *curr_esc = g_markup_escape_text(curr_utf8, -1);
            char *next_esc = g_markup_escape_text(next_utf8, -1);
            g_string_append_printf(str, "<span background='#ffcc00' foreground='black'>%s%s</span>", curr_esc, next_esc);
            g_free(curr_utf8); g_free(next_utf8);
            g_free(curr_esc); g_free(next_esc);
            p = g_utf8_next_char(next_p);
            continue;
        }

        if (is_space(curr)) {
            int spaces = 0;
            const char *temp_p = p;
            while (*temp_p && is_space(g_utf8_get_char(temp_p))) {
                spaces++;
                temp_p = g_utf8_next_char(temp_p);
            }
            if (spaces > 1) {
                *out_multi = TRUE;
                g_string_append_printf(str, "<span background='#8a1b1b'>%*s</span>", spaces, "");
            } else {
                g_string_append(str, "<span background='#0f5c22'> </span>");
            }
            p = temp_p;
            continue;
        }

        char *curr_utf8 = g_ucs4_to_utf8(&curr, 1, NULL, NULL, NULL);
        char *escaped = g_markup_escape_text(curr_utf8, -1);
        g_string_append(str, escaped);
        g_free(curr_utf8);
        g_free(escaped);
        p = next_p;
    }
    return g_string_free(str, FALSE);
}

// --- Scanning & Sorting ---
void scan_dir(const char *path) {
    GDir *dir = g_dir_open(path, 0, NULL);
    if (!dir) return;
    const char *entry_name;
    while ((entry_name = g_dir_read_name(dir))) {
        char *full = g_build_filename(path, entry_name, NULL);
        if (g_file_test(full, G_FILE_TEST_IS_DIR)) {
            scan_dir(full);
        } else {
            FileItem *item = g_new(FileItem, 1);
            item->full_path = full;
            item->name = g_strdup(entry_name);
            item->checksum = compute_checksum(full);
            item->is_ignored = g_hash_table_contains(ignored_set, item->checksum);
            item->markup = generate_markup(entry_name, &item->has_multi_space, &item->has_bad_format, item->is_ignored);
            g_ptr_array_add(file_list, item);
            continue;
        }
        g_free(full);
    }
    g_dir_close(dir);
}

gint sort_func(gconstpointer a, gconstpointer b) {
    FileItem *ia = *(FileItem **)a;
    FileItem *ib = *(FileItem **)b;
    if (ia->is_ignored != ib->is_ignored) return ia->is_ignored - ib->is_ignored;
    if (ia->has_bad_format != ib->has_bad_format) return ib->has_bad_format - ia->has_bad_format;
    if (ia->has_multi_space != ib->has_multi_space) return ib->has_multi_space - ia->has_multi_space;
    return g_utf8_collate(ia->name, ib->name);
}

void refresh_list() {
    if (!current_root) return;
    GtkListStore *store = GTK_LIST_STORE(gtk_tree_view_get_model(GTK_TREE_VIEW(tree_view)));
    gtk_list_store_clear(store);
    g_ptr_array_set_size(file_list, 0);
    scan_dir(current_root);
    g_ptr_array_sort(file_list, sort_func);
    GtkTreeIter iter;
    for (guint i = 0; i < file_list->len; i++) {
        FileItem *item = g_ptr_array_index(file_list, i);
        gtk_list_store_append(store, &iter);
        gtk_list_store_set(store, &iter, 0, item->markup, 1, i, 2, item->name, -1);
    }
}

// --- Interaction (Batch Processing) ---
void on_batch_fix_spaces(GtkWidget *menuitem, gpointer user_data) {
    GtkTreeSelection *selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(tree_view));
    GtkTreeModel *model;
    GList *rows = gtk_tree_selection_get_selected_rows(selection, &model);
    GList *curr;
    int fixed_count = 0;

    GPtrArray *items_to_fix = g_ptr_array_new();

    for (curr = rows; curr != NULL; curr = curr->next) {
        GtkTreePath *path = (GtkTreePath *)curr->data;
        GtkTreeIter iter;
        if (gtk_tree_model_get_iter(model, &iter, path)) {
            gint idx;
            gtk_tree_model_get(model, &iter, 1, &idx, -1);
            FileItem *item = g_ptr_array_index(file_list, idx);
            g_ptr_array_add(items_to_fix, item);
        }
    }

    for (guint i = 0; i < items_to_fix->len; i++) {
        FileItem *item = g_ptr_array_index(items_to_fix, i);
        
        char *new_name = try_fix_spaces(item->name);
        if (new_name) {
            char *dir = g_path_get_dirname(item->full_path);
            char *new_full = g_build_filename(dir, new_name, NULL);
            
            if (g_rename(item->full_path, new_full) == 0) {
                fixed_count++;
            }
            
            g_free(dir);
            g_free(new_full);
            g_free(new_name);
        }
    }

    g_ptr_array_free(items_to_fix, TRUE);
    g_list_free_full(rows, (GDestroyNotify)gtk_tree_path_free);

    if (fixed_count > 0) {
        refresh_list();
        char msg[64];
        snprintf(msg, sizeof(msg), "Fixed spaces in %d files.", fixed_count);
        GtkWidget *dlg = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_OK, "%s", msg);
        gtk_dialog_run(GTK_DIALOG(dlg));
        gtk_widget_destroy(dlg);
    } else {
        GtkWidget *dlg = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_OK, "No double spaces found in selection.");
        gtk_dialog_run(GTK_DIALOG(dlg));
        gtk_widget_destroy(dlg);
    }
}

void on_toggle_ignore(GtkWidget *menuitem, gpointer data) {
    FileItem *item = (FileItem *)data;
    if (item->is_ignored) g_hash_table_remove(ignored_set, item->checksum);
    else g_hash_table_add(ignored_set, g_strdup(item->checksum));
    save_config();
    refresh_list();
}

gboolean on_button_press(GtkWidget *widget, GdkEventButton *event, gpointer user_data) {
    if (event->type == GDK_BUTTON_PRESS && event->button == 3) { // 右键
        GtkTreeSelection *selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(tree_view));
        
        GtkTreePath *path_clicked = NULL;
        if (gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(tree_view), event->x, event->y, &path_clicked, NULL, NULL, NULL)) {
            
            if (!gtk_tree_selection_path_is_selected(selection, path_clicked)) {
                gtk_tree_selection_unselect_all(selection);
                gtk_tree_selection_select_path(selection, path_clicked);
            }
            gtk_tree_path_free(path_clicked);
        }

        guint selected_count = gtk_tree_selection_count_selected_rows(selection);

        GtkWidget *menu = gtk_menu_new();
        GtkWidget *menuitem;
        GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
        GtkWidget *image;
        GtkWidget *label;

        if (selected_count > 1) {
            char label_text[64];
            snprintf(label_text, sizeof(label_text), "Fix Double Spaces (%d files)", selected_count);

            menuitem = gtk_menu_item_new();
            image = gtk_image_new_from_icon_name("gtk-convert", GTK_ICON_SIZE_MENU); // 使用转换图标
            label = gtk_label_new(label_text);
            
            gtk_container_add(GTK_CONTAINER(box), image);
            gtk_container_add(GTK_CONTAINER(box), label);
            gtk_container_add(GTK_CONTAINER(menuitem), box);

            g_signal_connect(menuitem, "activate", G_CALLBACK(on_batch_fix_spaces), NULL);
            gtk_menu_shell_append(GTK_MENU_SHELL(menu), menuitem);

        } else if (selected_count == 1) {
            GtkTreeModel *model;
            GtkTreeIter iter;
            GList *rows = gtk_tree_selection_get_selected_rows(selection, &model);
            if (rows) {
                GtkTreePath *path = (GtkTreePath *)rows->data;
                gtk_tree_model_get_iter(model, &iter, path);
                gint idx;
                gtk_tree_model_get(model, &iter, 1, &idx, -1);
                FileItem *item = g_ptr_array_index(file_list, idx);

                menuitem = gtk_menu_item_new();
                if (item->is_ignored) {
                    image = gtk_image_new_from_icon_name("gtk-apply", GTK_ICON_SIZE_MENU);
                    label = gtk_label_new("Enable Highlight");
                } else {
                    image = gtk_image_new_from_icon_name("gtk-cancel", GTK_ICON_SIZE_MENU);
                    label = gtk_label_new("Cancel Highlight");
                }
                gtk_container_add(GTK_CONTAINER(box), image);
                gtk_container_add(GTK_CONTAINER(box), label);
                gtk_container_add(GTK_CONTAINER(menuitem), box);
                
                g_signal_connect(menuitem, "activate", G_CALLBACK(on_toggle_ignore), item);
                gtk_menu_shell_append(GTK_MENU_SHELL(menu), menuitem);
                
                g_list_free_full(rows, (GDestroyNotify)gtk_tree_path_free);
            }
        }

        gtk_widget_show_all(menu);
        gtk_menu_popup_at_pointer(GTK_MENU(menu), (GdkEvent*)event);
        return TRUE;
    }
    return FALSE;
}

void on_rename_confirm(GtkCellRendererText *cell, gchar *path_str, gchar *new_text, gpointer data) {
    GtkTreeModel *model = gtk_tree_view_get_model(GTK_TREE_VIEW(tree_view));
    GtkTreeIter iter;
    if (!gtk_tree_model_get_iter_from_string(model, &iter, path_str)) return;
    gint idx;
    gtk_tree_model_get(model, &iter, 1, &idx, -1);
    FileItem *item = g_ptr_array_index(file_list, idx);
    if (strlen(new_text) == 0 || strcmp(new_text, item->name) == 0) return;
    char *dir = g_path_get_dirname(item->full_path);
    char *new_full = g_build_filename(dir, new_text, NULL);
    if (g_rename(item->full_path, new_full) == 0) refresh_list();
    else {
        GtkWidget *dlg = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR, GTK_BUTTONS_OK, "Rename Failed!");
        gtk_dialog_run(GTK_DIALOG(dlg));
        gtk_widget_destroy(dlg);
    }
    g_free(dir);
    g_free(new_full);
}

gboolean on_key_press(GtkWidget *w, GdkEventKey *e, gpointer d) {
    if (e->keyval == GDK_KEY_F2) {
        GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(tree_view));
        GtkTreeModel *model; GtkTreeIter iter;
        if (gtk_tree_selection_get_selected(sel, &model, &iter)) {
            GtkTreePath *path = gtk_tree_model_get_path(model, &iter);
            gtk_tree_view_set_cursor_on_cell(GTK_TREE_VIEW(tree_view), path, col_name, rend_name, TRUE);
            gtk_tree_path_free(path);
            return TRUE;
        }
    }
    return FALSE;
}

void on_select_dir(GtkWidget *w, gpointer d) {
    GtkWidget *dlg = gtk_file_chooser_dialog_new("Select Directory", GTK_WINDOW(gtk_widget_get_toplevel(w)),
        GTK_FILE_CHOOSER_ACTION_SELECT_FOLDER, "Cancel", GTK_RESPONSE_CANCEL, "Select", GTK_RESPONSE_ACCEPT, NULL);
    if (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_ACCEPT) {
        g_free(current_root);
        current_root = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dlg));
        refresh_list();
    }
    gtk_widget_destroy(dlg);
}

// --- Main ---
int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    apply_dark_theme();

    file_list = g_ptr_array_new_with_free_func(free_item);
    ignored_set = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, NULL);
    load_config();

    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(win), "Doujinshi-Format Scanner");
    gtk_window_set_default_size(GTK_WINDOW(win), 800, 600);
    g_signal_connect(win, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(win), vbox);

    GtkWidget *btn = gtk_button_new_with_label("Select Directory");
    gtk_widget_set_margin_top(btn, 10);
    gtk_widget_set_margin_bottom(btn, 10);
    gtk_widget_set_margin_start(btn, 10);
    gtk_widget_set_margin_end(btn, 10);
    g_signal_connect(btn, "clicked", G_CALLBACK(on_select_dir), NULL);
    gtk_box_pack_start(GTK_BOX(vbox), btn, FALSE, FALSE, 0);

    GtkListStore *store = gtk_list_store_new(3, G_TYPE_STRING, G_TYPE_INT, G_TYPE_STRING);
    tree_view = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    
    GtkTreeSelection *selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(tree_view));
    gtk_tree_selection_set_mode(selection, GTK_SELECTION_MULTIPLE);

    g_signal_connect(tree_view, "key-press-event", G_CALLBACK(on_key_press), NULL);
    g_signal_connect(tree_view, "button-press-event", G_CALLBACK(on_button_press), NULL);

    rend_name = gtk_cell_renderer_text_new();
    g_object_set(rend_name, "editable", TRUE, NULL);
    g_signal_connect(rend_name, "edited", G_CALLBACK(on_rename_confirm), NULL);

    col_name = gtk_tree_view_column_new();
    gtk_tree_view_column_set_title(col_name, "Filename");
    gtk_tree_view_column_pack_start(col_name, rend_name, TRUE);
    gtk_tree_view_column_add_attribute(col_name, rend_name, "markup", 0);
    gtk_tree_view_column_add_attribute(col_name, rend_name, "text", 2);
    gtk_tree_view_append_column(GTK_TREE_VIEW(tree_view), col_name);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), tree_view);
    gtk_box_pack_start(GTK_BOX(vbox), scroll, TRUE, TRUE, 0);

    gtk_widget_show_all(win);
    gtk_main();

    g_ptr_array_free(file_list, TRUE);
    g_hash_table_destroy(ignored_set);
    return 0;
}
