$(document).ready(function() {
	$('form input[type="text"]').not('[readonly=readonly]').first().select().focus();
	$('div.flash-message').hide().slideDown().delay(5000).slideUp();
	$('div.flash-error').hide().slideDown();
	//$('input[type="submit"]').button();
	$('a.btn-back').button({ icons: { primary: 'ui-icon-arrowreturn-1-w' }});
	$('a.btn-add').button({ icons: { primary: 'ui-icon-plus' }});
	$('a.btn-del').button({ icons: { primary: 'ui-icon-circle-close' }});
	$('a.btn-edit').button({ icons: { primary: 'ui-icon-pencil' }});
	$('a.btn-mod').button({ icons: { primary: 'ui-icon-cancel' }});
	$('a.btn-moderate').button({ icons: { primary: 'ui-icon-pencil' }});
	$('a.btn-check').button({ icons: { primary: 'ui-icon-circle-check' }});
	$('a.btn-search').button({ icons: { primary: 'ui-icon-search' }});
	$('a.btn-big').button()

	$('input[name="dt_start"]').datetimepicker({
		'dateFormat': 'yy-mm-dd',
		'timeFormat': 'hh:mm:ss',
		'separator': ' '
	});
	
	$('input[name="dt_end"]').datetimepicker({
		'dateFormat': 'yy-mm-dd',
		'timeFormat': 'hh:mm:ss',
		'separator': ' '
	});
	
	$('input[name="dt_event"]').datetimepicker({
		'dateFormat': 'yy-mm-dd',
		'timeFormat': 'hh:mm:ss',
		'separator': ' '
	});

	$(' [placeholder] ').defaultValue();

	$('#expertmode').click(function() {
		$('#expertdiv').show();
		$('#expertmode').hide();
	})
});
