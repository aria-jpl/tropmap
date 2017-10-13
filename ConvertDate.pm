# SOPAC::ConvertDate.pm              -*- Perl -*-
package ConvertDate;

sub gwk2ydoy {
  # ------------------------------------------------------
  # gwk2ydoy converts either from yyyy doy to gwk dow
  #                       or from gwk dow to yyyy doy
  # by pfang@ucsd.edu
  # ------------------------------------------------------
  my ($ar1,$ar2) = @_;
  my @darray = (366,365,365,365);
  my $doys = \@darray;
  my $yroff = 1980;
  my $dayoff = 6;
  my ($i,$j);

  my $mjd010580=44243;	
  # check which type of conversion
  if ($ar1 >= $yroff) {
    $mjd = mjd2ydoy($ar1,$ar2) - $mjd010580 - 1;
    $gweek = int($mjd / 7);
    $dow = $mjd % 7;
    return(sprintf("%0004.0f",$gweek),$dow);
  } else {
    # convert from gwk dow to yy doy
    $j = $ar1 * 7 + $ar2 + $dayoff;
    $i = $yroff;
    while ($j > $$doys[$i % 4]) {
      $j -= $$doys[$i++ % 4];
    }
    return(sprintf("%4.4d",$i),sprintf("%003.0f",$j));
  }
}



sub mjd2ydoy {
  # ------------------------------------------------------
  # mjd2yday converts either from yyyy doy to mjd
  #                       or from mjd to yyyy doy
  # by pfang@ucsd.edu
  # ------------------------------------------------------
  my ($ar1,$ar2) = @_;
  my @darray = (366,365,365,365);
  my $doys = \@darray;
  my $jd52 = 34011;
  my $yy = 1952;
  my ($i,$doy);
  # check which type of conversion
  if ($ar2 == 0) {
    # convert from mjd to yy doy
    $doy = $ar1 - $jd52;
    $i = 0;
    while ($doy > $$doys[$i]) {
      $doy -= $$doys[$i];
      $i = ++$yy % 4;
    }
    return ($yy,sprintf("%3.3d",$doy));
  } else {
    # convert from yy doy to mjd
    $yy = $ar1 - $yy;
    $mjd = $jd52 + $yy * 365 + int(($yy + 3) / 4) + $ar2;
    return ($mjd);
  }
}



sub ymd2ydoy {
  # ------------------------------------------------------
  # ymd2ydoy converts either from yyyy doy to yyyy mm dd
  #                       or from yyyy mm dd to yyyy doy
  # by pfang@ucsd.edu
  # ------------------------------------------------------
  my ($ar1,$ar2,$ar3) = @_;
  my @mth = ([0,31,28,31,30,31,30,31,31,30,31,30,31],
	     [0,31,29,31,30,31,30,31,31,30,31,30,31]);
  my $m = \@mth;
  my ($i, $doy);
  my $leapi = 0;
	
  # see if it is a leap year
  if (($ar1-1904) % 4 == 0) {
    $leapi = 1;
  }
  # test which type of conversion
  if ($ar3 == 0) {
    # convert from yyyy doy to yyyy mm dd
    for ($i=0; $ar2>$$m[$leapi][$i]; $i++) {
      $ar2 -= $$m[$leapi][$i];
    }
    return ($ar1,sprintf("%02.0f",$i),sprintf("%02.0f",$ar2));
  } else {
    # convert from yyyy mm dd to yyyy doy
    for ($i=1; $i<$ar2; $i++) {
      $doy += $$m[$leapi][$i];
    }
    $doy += $ar3;
    return ($ar1,sprintf("%003.0f",$doy),0);
  }
}

sub mjd2decyr {
# ------------------------------------------------------
# mjd2decyr converts either from yyyy.yyy to mjd
#                       or from mjd to yyyy.yyy
# by mvandomselaar@ucsd.edu
# ------------------------------------------------------
	my ($ar1,$ar2) = @_;
	my @darray = (366,365,365,365);
	my $doys = \@darray;
	my $jd52 = 34011;
	my $yy = 1952;
	my ($i,$doy);
	# check which type of conversion
	if ($ar1 =~ /^(\d{5})/ ) {
		# convert from mjd to yyyy.yyyy
		$doy = $ar1 - $jd52;
		$i = 0;
		while ($doy > $$doys[$i]) {
			$doy -= $$doys[$i];
			$i = ++$yy % 4;
		}
		$doy = sprintf("%003.0f",$doy);
		$decyr = sprintf("%8.4f", $yy + $doy/365.249);
		return($decyr);
	} else {
		# convert from yyyy.yyyy doy to mjd
		$ar2 = substr($ar1, 4);
		$ar1 = substr($ar1, 0, 4);
		$ar2 = int(($ar2 * 365.249) + 0.51);
		$yy = $ar1 - $yy;
		$mjd = $jd52 + $yy * 365 + int(($yy + 3) / 4) + $ar2;
		return ($mjd);
	}

} # end of mjd2decyr


sub ydoy2decyr {
# ------------------------------------------------------
# ydoy2decyr converts from yyyy ddd to yyyy.yyyy
# by pjamason@ucsd.edu, 12/18/2002
# ------------------------------------------------------
    my ($year,$doy) = @_;
    $doy = $doy + 0;
    $year = $year + 0;
    my ($daysInYear) = 365;
    if ($year % 4 == 0) {
	$daysInYear = 366;
    }

    # pj, 05/29/2003: this will return year+1 for last day of year
    # all other code seems to do this... ok

    # pj, 03/09/2005: change all dates to day - 0.5.  
    # midpoint of day 1 should be 0.5, not 1.5
    #my ($decYr) = $year + ($doy/$daysInYear);
    my ($decYr) = $year + (($doy - 0.5)/$daysInYear);
    $decYr = sprintf "%.4f", $decYr;
    return($decYr);
}


sub decyr2ydoy {
# ------------------------------------------------------
# decyr2ydoy converts from yyyy.yyyy to yyyy ddd
# by pjamason@ucsd.edu, 12/19/2002
# ------------------------------------------------------

    my ($yearDecYr) = @_;
    
    # pj added, 08/13/2003: we need to pad zeroes here; for ex.,
    # if 1999.7 is passed, it previously used 7 for decYr, not
    # 7000.
    $yearDecYr = sprintf "%9.4f", $yearDecYr;


    my ($year,$decYr) = split(/\./,$yearDecYr);
    $decYr = $decYr / 10000;

    $year = $year + 0;

    my ($daysInYear) = 365;
    if ($year % 4 == 0) {
	$daysInYear = 366;
    }

    my ($doy);
    
    $decYr = ($decYr + $HALFDAY) * $daysInYear;

    # pj, 03/09/2005: when we drop fifth significant digit on ref epoch,
    # we come up short on integer day when we multiply by days in year.
    # add .05
    $doy = int($decYr + .05);

    $doy = &SOPAC::Utils::formatDay($doy);
	
    if ($doy eq "000"){$doy = "001"};
    
    return ($year,$doy);
}


sub ydoy2xsddate {
# ------------------------------------------------------
# ydoy2xsddate: from yyyy ddd to xsd date format (yyyy-mm-ddThh:mm:ss)
# by pjamason@ucsd.edu, 03/02/2005
# ------------------------------------------------------
    my ($year,$doy) = @_;

    use DateTime::Precise;

    $doy = $doy + 0;
    $year = $year + 0;
    my ($hour,$min,$sec) = 0;

    my ($dt) = DateTime::Precise->new('YDHMS',$year,$doy,$hour,$min,$sec);
    my ($xsdDate) = $dt->strftime("%Y-%m-%dT%T");
    return($xsdDate);
}

sub xsddate2ydoy {
# ------------------------------------------------------
# xsddate2ydoy: from xsd date format (yyyy-mm-ddThh:mm:ss) to yyyy ddd
# by pjamason@ucsd.edu, 03/09/2005
# ------------------------------------------------------
    my ($xsdDate) = @_;

    use DateTime::Precise;

    my ($year) = substr($xsdDate,0,4);
    my ($mon) = substr($xsdDate,5,2);
    my ($day) = substr($xsdDate,8,2);
    my ($tmp,$doy) = &ymd2ydoy($year,$mon,$day);
    return($year,$doy);
}




1;







