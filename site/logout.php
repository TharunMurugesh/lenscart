<?php
require __DIR__ . '/inc/auth.php';
logout_user();
redirect('index.php');
