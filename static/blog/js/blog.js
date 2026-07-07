$(document).ready(function() {
    // ----------------------------------------------------
    // Utility functions to manage validation error displays
    // ----------------------------------------------------
    function clearFormErrors(form) {
        $(form).find('.is-invalid').removeClass('is-invalid');
        $(form).find('.invalid-feedback').addClass('d-none').html('');
    }

    function displayFormErrors(form, errors, prefix) {
        clearFormErrors(form);
        $.each(errors, function(field, messages) {
            var inputId = '#id_' + prefix + '_' + field;
            var errorId = '#error_' + prefix + '_' + field;
            $(inputId).addClass('is-invalid');
            $(errorId).removeClass('d-none').html(messages.join('<br>'));
        });
    }

    // Clear individual field errors when user edits the input
    $('form').on('input change', 'input, select, textarea', function() {
        $(this).removeClass('is-invalid');
        var fieldName = $(this).attr('name');
        var formId = $(this).closest('form').attr('id');
        var prefix = formId === 'create-blog-form' ? 'create' : 'edit';
        $('#error_' + prefix + '_' + fieldName).addClass('d-none').html('');
    });

    // ----------------------------------------------------
    // Initialize Plugins for Edit Modal
    // ----------------------------------------------------
    // Summernote rich text editor
    $('#id_edit_content').summernote({
        tabsize: 2,
        height: 200,
        toolbar: [
            ['font', ['bold', 'underline', 'italic']],
            ['fontname', ['fontname']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['insert', ['link']],
            ['view', ['codeview', 'help']]
        ]
    });

    // Select2 tags multiselect (modal aware dropdownParent)
    $('#id_edit_tags').select2({
        tags: true,
        tokenSeparators: [',', ' '],
        placeholder: 'Enter tags...',
        width: '100%',
        dropdownParent: $('#editBlogModal')
    });

    // ----------------------------------------------------
    // Edit Blog Modal Population Handler
    // ----------------------------------------------------
    $('#blog-datatable').on('click', '.edit-blog-btn', function() {
        var button = $(this);
        var blogId = button.data('id');
        var editUrl = button.data('url');
        var editForm = $('#edit-blog-form');

        // Clear previous validations
        clearFormErrors(editForm);

        // Bind the form action URL to match the dynamic edit URL
        editForm.attr('action', editUrl);

        // Fetch details from backend via GET request
        $.ajax({
            url: editUrl,
            type: 'GET',
            success: function(response) {
                if (response.success && response.data) {
                    var data = response.data;
                    
                    // Populate text/select fields
                    $('#edit-blog-id').val(data.id);
                    $('#id_edit_title').val(data.title);
                    $('#id_edit_category').val(data.category);

                    // Load content into Summernote editor
                    $('#id_edit_content').summernote('code', data.content || '');

                    // Pre-populate Select2 tags
                    var tagsSelect = $('#id_edit_tags');
                    tagsSelect.empty();
                    if (data.tags) {
                        $.each(data.tags, function(idx, val) {
                            var newOption = new Option(val, val, true, true);
                            tagsSelect.append(newOption);
                        });
                    }
                    tagsSelect.trigger('change');

                    // Map publish checkbox state
                    $('#id_edit_publish').prop('checked', data.publish);

                    // Show image preview label if existing cover exists
                    if (data.image_url) {
                        $('#edit-image-help').html(
                            'Current image: <a href="' + data.image_url + '" target="_blank">' + 
                            data.image_url.split('/').pop() + '</a>'
                        );
                    } else {
                        $('#edit-image-help').html('No cover image currently uploaded.');
                    }

                    // Open the Edit modal
                    $('#editBlogModal').modal('show');
                }
            },
            error: function() {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Unable to retrieve blog post details. Please try again.'
                });
            }
        });
    });

    // ----------------------------------------------------
    // Edit Blog AJAX Form Submission Handler
    // ----------------------------------------------------
    $('#edit-blog-form').on('submit', function(e) {
        e.preventDefault();

        // Sync Summernote editor code to textarea tag for validation serialization
        $('#id_edit_content').val($('#id_edit_content').summernote('code'));

        var form = this;
        var formData = new FormData(form);
        var submitBtn = $('#edit-submit-btn');
        var originalBtnText = submitBtn.html();
        var postUrl = $(form).attr('action');

        // Lock form and display processing loading spinner
        submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...');

        var csrfToken = $(form).find('input[name="csrfmiddlewaretoken"]').val();

        $.ajax({
            url: postUrl,
            type: 'PUT',
            headers: {
                'X-CSRFToken': csrfToken
            },
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                // Reset loading state
                submitBtn.prop('disabled', false).html(originalBtnText);
                
                // Hide modal and clear validation markers
                $('#editBlogModal').modal('hide');
                form.reset();
                clearFormErrors(form);

                // Reload DataTable asynchronously
                if ($.fn.DataTable.isDataTable('#blog-datatable')) {
                    $('#blog-datatable').DataTable().ajax.reload(null, false);
                }

                // Show SweetAlert2 Success alert
                Swal.fire({
                    icon: 'success',
                    title: 'Updated!',
                    text: response.message || 'Blog post updated successfully.',
                    timer: 2000,
                    showConfirmButton: false,
                    toast: true,
                    position: 'top-end'
                });
            },
            error: function(xhr) {
                // Reset loading state
                submitBtn.prop('disabled', false).html(originalBtnText);

                if (xhr.status === 400 && xhr.responseJSON && xhr.responseJSON.errors) {
                    // Display validation errors and keep modal open
                    displayFormErrors(form, xhr.responseJSON.errors, 'edit');
                } else {
                    // Display generic system server error alert
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: 'An unexpected system error occurred. Please try again.'
                    });
                }
            }
        });
    });

    // ----------------------------------------------------
    // Delete Blog AJAX Form Handler
    // ----------------------------------------------------
    $('#blog-datatable').on('click', '.delete-blog-btn', function() {
        var button = $(this);
        var blogId = button.data('id');
        var deleteUrl = button.data('url');
        var csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

        // Trigger SweetAlert2 confirmation modal
        Swal.fire({
            title: 'Are you sure?',
            text: "This blog post will be permanently deleted and cannot be undone.",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, delete it!',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                // Show dynamic deletion processing status spinner
                Swal.fire({
                    title: 'Deleting post...',
                    allowOutsideClick: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });

                // Issue AJAX DELETE request to perform database deletion
                $.ajax({
                    url: deleteUrl,
                    type: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    success: function(response) {
                        // Reload DataTable asynchronously
                        if ($.fn.DataTable.isDataTable('#blog-datatable')) {
                            $('#blog-datatable').DataTable().ajax.reload(null, false);
                        }

                        // Close processing alerts and display success toast in top corner
                        Swal.fire({
                            icon: 'success',
                            title: 'Deleted!',
                            text: response.message || 'Blog post has been deleted.',
                            timer: 2000,
                            showConfirmButton: false,
                            toast: true,
                            position: 'top-end'
                        });
                    },
                    error: function() {
                        Swal.fire({
                            icon: 'error',
                            title: 'Error',
                            text: 'An unexpected server error occurred while deleting. Please try again.'
                        });
                    }
                });
            }
        });
    });

    // ----------------------------------------------------
    // Intercept topbar search form submit events on list view
    // ----------------------------------------------------
    $('#topbar-search-form').on('submit', function(e) {
        if ($.fn.DataTable.isDataTable('#blog-datatable')) {
            e.preventDefault();
            var query = $('#topbar-search-input').val();
            $('#blog-datatable').DataTable().search(query).draw();
        }
    });

    // ----------------------------------------------------
    // Category dropdown filter click handler
    // ----------------------------------------------------
    $('.category-filter-item').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation(); // Keep dropdown open for fluid multi-select experience

        var clickedCat = $(this).data('category');

        if (clickedCat === 'All') {
            // "All Categories" clicked -> deselect others
            $('.category-filter-item').removeClass('active');
            $(this).addClass('active');
        } else {
            // Specific category clicked -> toggle active class
            $(this).toggleClass('active');
            $('.category-filter-item[data-category="All"]').removeClass('active');

            // Fallback to "All Categories" if everything else is deselected
            var activeSpecificCount = $('.category-filter-item.active').not('[data-category="All"]').length;
            if (activeSpecificCount === 0) {
                $('.category-filter-item[data-category="All"]').addClass('active');
            }
        }

        // Update button label dynamic count
        var activeCount = $('.category-filter-item.active').not('[data-category="All"]').length;
        if (activeCount === 0) {
            $('#current-filter-label').text('Filter');
        } else {
            $('#current-filter-label').text('Filter (' + activeCount + ')');
        }

        // Reload DataTable to query server-side view with extra data
        if ($.fn.DataTable.isDataTable('#blog-datatable')) {
            $('#blog-datatable').DataTable().ajax.reload();
        }
    });
});
