#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>
#include <glib/gstdio.h>

typedef struct {
    char *full_path;
    char *name;
    char *markup;
    gboolean has_multi_space;
} FileItem;

GPtrArray *file_list = NULL;
char *current_root = NULL;
GtkWidget *tree_view;
GtkTreeViewColumn *col_name;
GtkCellRenderer *rend_name;

void free_item(gpointer data) {
    FileItem *item = (FileItem *)data;
    g_free(item->full_path);
    g_free(item->name);
    g_free(item->markup);
    g_free(item);
}

char* generate_markup(const char *name, gboolean *multi_space) {
    GString *str = g_string_new("");
    int len = strlen(name);
    int i = 0;
    *multi_space = FALSE;

    while (i < len) {
        if (name[i] == ' ') {
            int spaces = 0;
            while (i < len && name[i] == ' ') { spaces++; i++; }
            
            if (spaces > 1) {
                *multi_space = TRUE;
                g_string_append_printf(str, "<span background='#8a1b1b'>%*s</span>", spaces, "");
            } else {
                g_string_append(str, "<span background='#0f5c22'> </span>");
            }
        } else {
            int j = i;
            while (j < len && name[j] != ' ') j++;
            char *chunk = g_strndup(name + i, j - i);
            char *escaped = g_markup_escape_text(chunk, -1);
            g_string_append(str, escaped);
            g_free(chunk);
            g_free(escaped);
            i = j;
        }
    }
    return g_string_free(str, FALSE);
}

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
            item->markup = generate_markup(entry_name, &item->has_multi_space);
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
    if (ia->has_multi_space != ib->has_multi_space)
        return ib->has_multi_space - ia->has_multi_space;
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

    if (g_rename(item->full_path, new_full) == 0) {
        refresh_list();
    } else {
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

void apply_dark_theme() {
    GtkSettings *settings = gtk_settings_get_default();
    g_object_set(settings, "gtk-application-prefer-dark-theme", TRUE, NULL);

    GtkCssProvider *provider = gtk_css_provider_new();
    
    const char *css =
        "window { background-color: #1e1e1e; color: #cccccc; }"
        "treeview { background-color: #252526; color: #cccccc; }"
        "treeview:selected { background-color: #094771; color: #ffffff; }"
        "button { background-color: #3c3c3c; color: #ffffff; border: 1px solid #2d2d2d; }"
        "button:hover { background-color: #505050; }"
        "header { background-color: #2d2d2d; color: #cccccc; }"
        "entry { background-color: #3c3c3c; color: #ffffff; border: 1px solid #474747; }";

    gtk_css_provider_load_from_data(provider, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(gdk_screen_get_default(),
                                              GTK_STYLE_PROVIDER(provider),
                                              GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(provider);
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    apply_dark_theme();

    file_list = g_ptr_array_new_with_free_func(free_item);

    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(win), "Space Checker");
    gtk_window_set_default_size(GTK_WINDOW(win), 600, 500);
    g_signal_connect(win, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *vbox = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(win), vbox);

    GtkWidget *btn = gtk_button_new_with_label("Select a directory");

    gtk_widget_set_margin_top(btn, 10);
    gtk_widget_set_margin_bottom(btn, 10);
    gtk_widget_set_margin_start(btn, 10);
    gtk_widget_set_margin_end(btn, 10);
    g_signal_connect(btn, "clicked", G_CALLBACK(on_select_dir), NULL);
    gtk_box_pack_start(GTK_BOX(vbox), btn, FALSE, FALSE, 0);

    GtkListStore *store = gtk_list_store_new(3, G_TYPE_STRING, G_TYPE_INT, G_TYPE_STRING);
    tree_view = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    g_signal_connect(tree_view, "key-press-event", G_CALLBACK(on_key_press), NULL);

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
    return 0;
}