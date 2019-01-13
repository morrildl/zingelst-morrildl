<?xml version='1.0'?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="/">	
	<fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format">
	    <fo:layout-master-set>
		    <fo:simple-page-master master-name="my-page">
			 <fo:region-body margin="0.75cm"/>
		    </fo:simple-page-master>
	    </fo:layout-master-set>

	    <fo:page-sequence master-reference="my-page">
		<fo:flow flow-name="xsl-region-body">
		    <xsl:for-each select="card-list/card">	  
			<xsl:variable name="posn" select="position()"/>
			<xsl:variable name="xpos" select="((position()-1) mod 3)"/>
			<xsl:variable name="ypos" select="(floor((position()-1) div 3)) mod 3"/>
			<xsl:variable name="top" select="$ypos * 3.51 "/>
			<xsl:variable name="left" select="$xpos * 2.51"/>

			<xsl:if test="$xpos = 0 and $ypos = 0 and position() > 1">
			    <xsl:text disable-output-escaping="yes"><![CDATA[<fo:block break-after="page"/>]]></xsl:text>
			</xsl:if>

			<fo:block-container position="absolute"
					    top="{$top}in" height="3.5in" left="{$left}in" width="2.5in"
					    border="solid blue 0.01in"/>
			<fo:block-container position="absolute"
					    top="{$top + 0.01}in" left="{$left + 0.01}in" width="2.48in" height="0.25in"
					    display-align="center" background-color="#99ff99">
			    <fo:block><xsl:value-of select="title"/></fo:block>
			</fo:block-container>
			<fo:block-container position="absolute" top="{$top + 0.01 + 0.25}in" left="{$left + 0.01}in"
					    width="2.48in" height="1.25in"
					    background-color="#ff9999">
			    <fo:block text-align="center" display-align="center">
				Insert Picture Here
			    </fo:block>
			</fo:block-container>
			<fo:block-container position="absolute"
					    top="{$top + 0.01 + 1.50}in" left="{$left + 0.01}in"
					    width="2.48in" height="1.98in"
					    display-align="center" background-color="#ffff99">
			    <fo:block><xsl:value-of select="notes"/></fo:block>
			</fo:block-container>
		    </xsl:for-each>
		</fo:flow>
	    </fo:page-sequence>
	</fo:root>
    </xsl:template>
</xsl:stylesheet>
